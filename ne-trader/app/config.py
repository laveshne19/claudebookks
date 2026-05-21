"""Configuration loader for NE Kite Autotrader.

Loads settings from the ``.env`` file (via ``python-dotenv``) and exposes a
typed, validated :class:`Config` singleton. No secrets are hard-coded; every
value originates from the environment.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Project root is the ne-trader/ directory (parent of app/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 30-stock watchlist (all NSE EQUITY, MIS, 15-min candles) per spec.
WATCHLIST: List[str] = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK",
    "KOTAKBANK", "HCLTECH", "WIPRO", "BHARTIARTL", "ITC", "HINDUNILVR",
    "ASIANPAINT", "MARUTI", "TATASTEEL", "TATAMOTORS", "SUNPHARMA",
    "BAJFINANCE", "BAJAJFINSV", "ADANIENT", "LT", "ONGC", "NTPC",
    "POWERGRID", "ULTRACEMCO", "NESTLEIND", "DRREDDY", "CIPLA", "BPCL",
]


def _get_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid float for %s=%r; using default %s", key, raw, default)
        return default


def _get_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for %s=%r; using default %s", key, raw, default)
        return default


@dataclass(frozen=True)
class Config:
    """Immutable, validated application configuration.

    Attributes mirror the keys documented in ``.env.example``. Use
    :func:`load_config` to construct from the environment.
    """

    # Kite
    kite_api_key: str
    kite_api_secret: str
    kite_access_token: str

    # Anthropic
    anthropic_api_key: str
    anthropic_model: str

    # Trading
    live_mode: bool
    total_capital: float
    risk_per_trade_pct: float
    daily_loss_limit_pct: float
    min_confidence: float
    max_open_positions: int

    # Dashboard
    dashboard_username: str
    dashboard_password: str
    dashboard_port: int
    dashboard_bind: str

    # Scan
    scan_interval_seconds: int
    instrument_refresh_hours: int

    # Paths
    db_path: Path
    log_dir: Path

    watchlist: List[str] = field(default_factory=lambda: list(WATCHLIST))

    @property
    def paper_mode(self) -> bool:
        """True when real-money trading is disabled (the safe default)."""
        return not self.live_mode

    @property
    def claude_enabled(self) -> bool:
        """True when an Anthropic API key is configured."""
        return bool(self.anthropic_api_key)


def load_config(env_file: Path | None = None) -> Config:
    """Load and validate configuration from the environment / ``.env``.

    Args:
        env_file: Optional explicit path to a dotenv file. Defaults to
            ``<project_root>/.env``.

    Returns:
        Config: The validated configuration object.

    Raises:
        ValueError: If a safety-critical bound is violated (e.g. confidence
            below the hard floor of 50%).
    """
    path = env_file or (PROJECT_ROOT / ".env")
    if path.exists():
        load_dotenv(path, override=False)
    else:
        logger.warning(".env not found at %s; relying on process environment", path)

    min_confidence = _get_float("MIN_CONFIDENCE", 60.0)
    # Hard floor: never allow confidence threshold below 50% (spec safety rule 4).
    if min_confidence < 50.0:
        raise ValueError(
            f"MIN_CONFIDENCE={min_confidence} violates the 50% hard floor"
        )

    risk_pct = _get_float("RISK_PER_TRADE_PCT", 2.0)
    if risk_pct <= 0 or risk_pct > 2.0:
        raise ValueError(
            f"RISK_PER_TRADE_PCT={risk_pct} must be in (0, 2.0]; 2% is the max"
        )

    db_raw = os.environ.get("TRADER_DB_PATH")
    db_path = (Path(db_raw).expanduser().resolve() if db_raw
               else PROJECT_ROOT / "data" / "trader.db")

    log_raw = os.environ.get("LOG_DIR")
    log_dir = (Path(log_raw).expanduser().resolve() if log_raw
               else PROJECT_ROOT / "logs")

    cfg = Config(
        kite_api_key=os.environ.get("KITE_API_KEY", ""),
        kite_api_secret=os.environ.get("KITE_API_SECRET", ""),
        kite_access_token=os.environ.get("KITE_ACCESS_TOKEN", ""),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
        live_mode=_get_bool("LIVE_MODE", False),
        total_capital=_get_float("TOTAL_CAPITAL", 100000.0),
        risk_per_trade_pct=risk_pct,
        daily_loss_limit_pct=_get_float("DAILY_LOSS_LIMIT_PCT", 5.0),
        min_confidence=min_confidence,
        max_open_positions=_get_int("MAX_OPEN_POSITIONS", 5),
        dashboard_username=os.environ.get("DASHBOARD_USERNAME", "admin"),
        dashboard_password=os.environ.get("DASHBOARD_PASSWORD", ""),
        dashboard_port=_get_int("DASHBOARD_PORT", 8000),
        dashboard_bind=os.environ.get("DASHBOARD_BIND", "127.0.0.1"),
        scan_interval_seconds=_get_int("SCAN_INTERVAL_SECONDS", 300),
        instrument_refresh_hours=_get_int("INSTRUMENT_REFRESH_HOURS", 24),
        db_path=db_path,
        log_dir=log_dir,
    )

    if cfg.live_mode:
        logger.warning("LIVE_MODE is ON — real-money trading enabled!")
    else:
        logger.info("Running in PAPER mode (LIVE_MODE off) — no real orders")
    return cfg
