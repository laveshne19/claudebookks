"""Central configuration loaded from environment / .env file.

Nothing here is secret by default. Real credentials (Dhan, Anthropic) are read
from the environment so they never get committed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # dotenv is optional
    pass


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    # --- Mode -------------------------------------------------------------
    # "paper" = simulated fills, zero financial risk (default, always safe).
    # "live"  = real orders through the broker. Requires explicit opt-in AND
    #            valid broker credentials.
    mode: str = os.getenv("TRADING_MODE", "paper").strip().lower()

    # Broker to use in live mode. Only "dhan" implemented for v1.
    broker: str = os.getenv("BROKER", "dhan").strip().lower()

    # --- Capital & risk guardrails ---------------------------------------
    starting_cash: float = _get_float("STARTING_CASH", 100_000.0)
    # Max rupee value deployed in a single trade.
    max_trade_value: float = _get_float("MAX_TRADE_VALUE", 5_000.0)
    # Max number of simultaneous open positions.
    max_open_positions: int = _get_int("MAX_OPEN_POSITIONS", 3)
    # Hard daily loss limit (rupees). Bot halts for the day when breached.
    daily_loss_limit: float = _get_float("DAILY_LOSS_LIMIT", 2_000.0)
    # Per-position stop-loss / take-profit as fractions of entry price.
    stop_loss_pct: float = _get_float("STOP_LOSS_PCT", 0.015)
    take_profit_pct: float = _get_float("TAKE_PROFIT_PCT", 0.03)

    # --- Universe & strategy ---------------------------------------------
    # Comma separated NSE symbols the bot is allowed to trade.
    symbols: list[str] = field(
        default_factory=lambda: [
            s.strip().upper()
            for s in os.getenv("SYMBOLS", "RELIANCE,TCS,INFY,HDFCBANK,SBIN").split(",")
            if s.strip()
        ]
    )
    strategy: str = os.getenv("STRATEGY", "sma_crossover").strip().lower()
    # How often the strategy loop runs, in seconds.
    loop_interval_seconds: int = _get_int("LOOP_INTERVAL_SECONDS", 30)

    # --- Credentials (live mode) -----------------------------------------
    dhan_client_id: str = os.getenv("DHAN_CLIENT_ID", "")
    dhan_access_token: str = os.getenv("DHAN_ACCESS_TOKEN", "")

    # --- Claude / Anthropic ----------------------------------------------
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # --- Misc -------------------------------------------------------------
    db_path: str = os.getenv("DB_PATH", "trading.db")
    # Auto-start the trading loop on server boot.
    autostart: bool = _get_bool("AUTOSTART", False)
    # Use synthetic price feed when no real market data source is configured.
    allow_synthetic_feed: bool = _get_bool("ALLOW_SYNTHETIC_FEED", True)

    @property
    def live_ready(self) -> bool:
        """True only when live mode is selected AND credentials are present."""
        if self.mode != "live":
            return False
        if self.broker == "dhan":
            return bool(self.dhan_client_id and self.dhan_access_token)
        return False

    @property
    def effective_mode(self) -> str:
        """Falls back to paper if live was requested without credentials."""
        return "live" if self.live_ready else "paper"


@lru_cache
def get_settings() -> Settings:
    return Settings()
