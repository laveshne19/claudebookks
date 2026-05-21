"""Migrate historical trades from a Google Sheets export into the DB.

Google Sheets cannot be read directly, so export your trade log to CSV or
Excel and run::

    python scripts/import_trades.py path/to/trades.csv [--dry-run]

The importer is column-name tolerant: it lowercases headers and matches common
aliases (e.g. ``side``/``action``, ``qty``/``quantity``, ``buy_price``/
``entry``). Imported rows are stored as CLOSED, real-money (paper_mode=0)
history with reason ``migrated``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

# Allow running as a plain script from the ne-trader/ directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from app import database  # noqa: E402

logger = logging.getLogger(__name__)

# Map normalized header aliases -> our schema column.
ALIASES: Dict[str, str] = {
    "symbol": "symbol", "ticker": "symbol", "stock": "symbol", "scrip": "symbol",
    "action": "action", "side": "action", "type": "action",
    "quantity": "quantity", "qty": "quantity", "shares": "quantity",
    "entry_price": "entry_price", "entry": "entry_price", "buy_price": "entry_price",
    "buyprice": "entry_price", "price": "entry_price",
    "exit_price": "exit_price", "exit": "exit_price", "sell_price": "exit_price",
    "sellprice": "exit_price",
    "stop_loss": "stop_loss", "sl": "stop_loss", "stoploss": "stop_loss",
    "pnl": "pnl", "profit": "pnl", "p&l": "pnl", "pl": "pnl", "net": "pnl",
    "timestamp": "timestamp", "date": "timestamp", "datetime": "timestamp",
    "time": "timestamp",
}


def _read(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(" ", "_")
        if key in ALIASES:
            renamed[col] = ALIASES[key]
    return df.rename(columns=renamed)


def _to_float(value: object) -> Optional[float]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(str(value).replace(",", "").replace("₹", "").strip())
    except (ValueError, TypeError):
        return None


def import_file(path: Path, dry_run: bool = False,
                db_path: Optional[Path] = None) -> int:
    """Import trades from a CSV/Excel file into the ``trades`` table.

    Args:
        path: Path to the export file.
        dry_run: If True, parse and report but do not write to the DB.
        db_path: Optional explicit DB path.

    Returns:
        int: Number of rows imported (or that would be, in dry-run).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If no ``symbol`` column can be identified.
    """
    if not path.exists():
        raise FileNotFoundError(path)
    df = _normalize_columns(_read(path))
    if "symbol" not in df.columns:
        raise ValueError(
            f"Could not find a symbol column. Headers seen: {list(df.columns)}"
        )

    if not dry_run:
        database.init_db(db_path)

    imported = 0
    rows = []
    for _, r in df.iterrows():
        symbol = str(r.get("symbol", "")).strip().upper()
        if not symbol or symbol == "NAN":
            continue
        action = str(r.get("action", "BUY")).strip().upper()
        action = "SELL" if action.startswith("S") else "BUY"
        qty = _to_float(r.get("quantity")) or 0
        entry = _to_float(r.get("entry_price")) or 0.0
        rows.append((
            str(r.get("timestamp", "")) or None,
            symbol, "NSE", "EQ", action, int(qty), entry,
            _to_float(r.get("exit_price")), _to_float(r.get("stop_loss")),
            _to_float(r.get("pnl")), "CLOSED", 0, None, "migrated", None,
        ))
        imported += 1

    if dry_run:
        logger.info("[DRY-RUN] Would import %d trades from %s", imported, path)
        for row in rows[:5]:
            logger.info("  sample: %s %s qty=%s entry=%s pnl=%s",
                        row[1], row[4], row[5], row[6], row[9])
        return imported

    with database.get_connection(db_path) as conn:
        conn.executemany(
            "INSERT INTO trades(timestamp, symbol, exchange, segment, action, "
            "quantity, entry_price, exit_price, stop_loss, pnl, status, "
            "paper_mode, confidence, reason, kite_order_id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
    logger.info("Imported %d trades from %s", imported, path)
    return imported


def main(argv: Optional[list] = None) -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Import historical trades")
    parser.add_argument("file", type=Path, help="CSV or Excel export path")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and report without writing")
    args = parser.parse_args(argv)
    try:
        import_file(args.file, dry_run=args.dry_run)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
