"""SQLite database layer for NE Kite Autotrader.

Uses the Python stdlib ``sqlite3`` module only (no ORM, per project spec).
Provides schema creation, connection helpers, and small typed accessors for
the ``config`` and ``bot_state`` key/value tables.

Run schema initialisation with::

    python -m app.database init
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Resolve the default DB path relative to the repository, allowing override via
# the environment so tests and alternate deployments don't touch the real file.
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trader.db"


def get_db_path() -> Path:
    """Return the configured SQLite database path.

    Honours the ``TRADER_DB_PATH`` environment variable when set, otherwise
    falls back to ``<repo>/data/trader.db``.

    Returns:
        Path: Absolute path to the SQLite database file.
    """
    raw = os.environ.get("TRADER_DB_PATH")
    return Path(raw).expanduser().resolve() if raw else _DEFAULT_DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    segment TEXT NOT NULL,
    action TEXT NOT NULL,           -- BUY or SELL
    quantity INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL,
    stop_loss REAL,
    pnl REAL,
    status TEXT NOT NULL,           -- OPEN, CLOSED, FAILED
    paper_mode INTEGER NOT NULL,    -- 0=live, 1=paper
    confidence REAL,
    reason TEXT,                    -- Why this trade was taken
    kite_order_id TEXT
);

CREATE TABLE IF NOT EXISTS scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    symbol TEXT NOT NULL,
    decision TEXT NOT NULL,         -- BUY, SELL, HOLD
    buy_score REAL,
    sell_score REAL,
    indicators_json TEXT,           -- Full indicator breakdown
    claude_used INTEGER             -- 0=rules, 1=Claude
);

CREATE TABLE IF NOT EXISTS bot_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_scan_log_timestamp ON scan_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
"""


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open a SQLite connection with sensible defaults.

    Enables WAL journaling (for safer concurrent dashboard reads while the
    trader writes) and a row factory so callers get dict-like rows.

    Args:
        db_path: Optional explicit path. Defaults to :func:`get_db_path`.

    Returns:
        sqlite3.Connection: An open connection. Caller is responsible for
        closing it (or using it as a context manager).
    """
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: Optional[Path] = None) -> Path:
    """Create all tables and indexes if they do not already exist.

    Idempotent: safe to call repeatedly.

    Args:
        db_path: Optional explicit path. Defaults to :func:`get_db_path`.

    Returns:
        Path: The path of the initialised database.
    """
    path = db_path or get_db_path()
    with get_connection(path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    logger.info("Database initialised at %s", path)
    return path


def get_state(key: str, default: Optional[str] = None,
              db_path: Optional[Path] = None) -> Optional[str]:
    """Read a value from the ``bot_state`` key/value table.

    Args:
        key: State key (e.g. ``kill_switch_triggered``).
        default: Value to return if the key is absent.
        db_path: Optional explicit DB path.

    Returns:
        The stored string value, or ``default`` if not present.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT value FROM bot_state WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row is not None else default


def set_state(key: str, value: str, db_path: Optional[Path] = None) -> None:
    """Upsert a value into the ``bot_state`` key/value table.

    Args:
        key: State key.
        value: String value to store.
        db_path: Optional explicit DB path.
    """
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO bot_state(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


def get_config(key: str, default: Optional[str] = None,
               db_path: Optional[Path] = None) -> Optional[str]:
    """Read a value from the ``config`` table.

    Args:
        key: Config key.
        default: Value to return if the key is absent.
        db_path: Optional explicit DB path.

    Returns:
        The stored string value, or ``default`` if not present.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row is not None else default


def set_config(key: str, value: str, db_path: Optional[Path] = None) -> None:
    """Upsert a value into the ``config`` table, refreshing ``updated_at``.

    Args:
        key: Config key.
        value: String value to store.
        db_path: Optional explicit DB path.
    """
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO config(key, value, updated_at) "
            "VALUES(?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = CURRENT_TIMESTAMP",
            (key, value),
        )
        conn.commit()


def _main(argv: list[str]) -> int:
    """CLI entry point: ``python -m app.database init``."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(argv) >= 1 and argv[0] == "init":
        path = init_db()
        logger.info("Done. Tables created in %s", path)
        return 0
    logger.error("Usage: python -m app.database init")
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
