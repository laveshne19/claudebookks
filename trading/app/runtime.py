"""Runtime wiring + live-reconfigurable settings.

Holds the single engine instance and its swappable parts (broker, data feed,
strategy, Claude analyst). The in-app Settings page calls `apply_settings()` to
update credentials/mode/strategy without restarting the process. Overrides are
persisted in the DB so they survive restarts; secrets are stored locally only.
"""
from __future__ import annotations

import secrets as _secrets
from dataclasses import dataclass, field

from .ai.claude import ClaudeAnalyst
from .auth import hash_password
from .brokers.dhan import DhanBroker
from .brokers.paper import PaperBroker
from .config import get_settings
from .db import Database
from .engine.risk import RiskManager
from .engine.trader import TradingEngine
from .market.data import build_provider
from .strategy.registry import get_strategy

_OVERRIDE_KEY = "runtime_overrides"
# Fields that, when changed, require rebuilding the broker + data feed.
_BROKER_KEYS = {"mode", "broker", "dhan_client_id", "dhan_access_token", "security_map", "symbols"}
# Fields that require rebuilding strategy / analyst.
_AI_KEYS = {"strategy", "anthropic_api_key", "anthropic_model"}
_RISK_KEYS = {"max_trade_value", "max_open_positions", "daily_loss_limit", "stop_loss_pct", "take_profit_pct"}

SECRET_FIELDS = {"dhan_access_token", "anthropic_api_key", "dashboard_password"}


@dataclass
class EffectiveConfig:
    mode: str
    broker: str
    symbols: list
    strategy: str
    starting_cash: float
    loop_interval_seconds: int
    paper_data_source: str
    allow_synthetic_feed: bool
    max_trade_value: float
    max_open_positions: int
    daily_loss_limit: float
    stop_loss_pct: float
    take_profit_pct: float
    dhan_client_id: str
    dhan_access_token: str
    security_map: dict
    anthropic_api_key: str
    anthropic_model: str
    dashboard_user: str
    dashboard_password_hash: str
    claude_decision_interval: int

    @property
    def live_ready(self) -> bool:
        if self.mode != "live":
            return False
        if self.broker == "dhan":
            return bool(self.dhan_client_id and self.dhan_access_token and self.security_map)
        return False

    @property
    def effective_mode(self) -> str:
        return "live" if self.live_ready else "paper"


class _Runtime:
    def __init__(self):
        self.db: Database | None = None
        self.cfg: EffectiveConfig | None = None
        self.engine: TradingEngine | None = None
        self.secret_key: str = ""

    # --- lifecycle -------------------------------------------------------
    def init(self, db: Database) -> None:
        self.db = db
        self.secret_key = db.get_state("secret_key") or _secrets.token_hex(32)
        db.set_state("secret_key", self.secret_key)

        import os

        s = get_settings()
        overrides = db.get_state(_OVERRIDE_KEY, {}) or {}
        # Seed a default dashboard login on first boot (from env or sane default).
        if "dashboard_user" not in overrides:
            overrides["dashboard_user"] = os.getenv("DASHBOARD_USER", "admin")
        if "dashboard_password_hash" not in overrides:
            overrides["dashboard_password_hash"] = hash_password(os.getenv("DASHBOARD_PASSWORD", "changeme"))
        db.set_state(_OVERRIDE_KEY, overrides)

        self.cfg = self._build_config(s, overrides)
        self._build_all()

    def _build_config(self, s, overrides: dict) -> EffectiveConfig:
        import os

        def ov(key, default):
            return overrides.get(key, default)

        return EffectiveConfig(
            mode=ov("mode", s.mode),
            broker=ov("broker", s.broker),
            symbols=ov("symbols", s.symbols),
            strategy=ov("strategy", s.strategy),
            starting_cash=ov("starting_cash", s.starting_cash),
            loop_interval_seconds=ov("loop_interval_seconds", s.loop_interval_seconds),
            paper_data_source=ov("paper_data_source", s.paper_data_source),
            allow_synthetic_feed=ov("allow_synthetic_feed", s.allow_synthetic_feed),
            max_trade_value=ov("max_trade_value", s.max_trade_value),
            max_open_positions=ov("max_open_positions", s.max_open_positions),
            daily_loss_limit=ov("daily_loss_limit", s.daily_loss_limit),
            stop_loss_pct=ov("stop_loss_pct", s.stop_loss_pct),
            take_profit_pct=ov("take_profit_pct", s.take_profit_pct),
            dhan_client_id=ov("dhan_client_id", s.dhan_client_id),
            dhan_access_token=ov("dhan_access_token", s.dhan_access_token),
            security_map=ov("security_map", _parse_security_map(os.getenv("SECURITY_MAP", ""))),
            anthropic_api_key=ov("anthropic_api_key", s.anthropic_api_key),
            anthropic_model=ov("anthropic_model", s.anthropic_model),
            dashboard_user=ov("dashboard_user", "admin"),
            dashboard_password_hash=ov("dashboard_password_hash", ""),
            claude_decision_interval=int(ov("claude_decision_interval", 300)),
        )

    def _build_all(self) -> None:
        c = self.cfg
        risk = RiskManager(
            max_trade_value=c.max_trade_value,
            max_open_positions=c.max_open_positions,
            daily_loss_limit=c.daily_loss_limit,
            stop_loss_pct=c.stop_loss_pct,
            take_profit_pct=c.take_profit_pct,
        )
        self.engine = TradingEngine(
            broker=self._make_broker(),
            data_provider=self._make_data(),
            strategy=self._make_strategy(),
            risk=risk,
            db=self.db,
            settings=c,
        )
        self.engine.analyst = self._make_analyst()

    def _make_broker(self):
        c = self.cfg
        if c.effective_mode == "live" and c.broker == "dhan":
            return DhanBroker(c.dhan_client_id, c.dhan_access_token, c.security_map)
        return PaperBroker(c.starting_cash)

    def _make_data(self):
        return build_provider(self.cfg)

    def _make_strategy(self):
        c = self.cfg
        if c.strategy == "claude_advisor":
            from .strategy.claude_strategy import ClaudeStrategy

            return ClaudeStrategy(
                api_key=c.anthropic_api_key,
                model=c.anthropic_model,
                decision_interval=c.claude_decision_interval,
            )
        return get_strategy(c.strategy)

    def _make_analyst(self) -> ClaudeAnalyst:
        return ClaudeAnalyst(self.cfg.anthropic_api_key, self.cfg.anthropic_model)

    # --- settings application -------------------------------------------
    def apply_settings(self, updates: dict) -> dict:
        """Merge updates, persist, and selectively rebuild affected parts.

        Empty-string secret fields are ignored (so blank inputs don't wipe an
        already-saved key/token).
        """
        overrides = self.db.get_state(_OVERRIDE_KEY, {}) or {}
        changed: set[str] = set()

        for k, v in updates.items():
            if k in SECRET_FIELDS and (v is None or v == ""):
                continue
            if k == "dashboard_password":
                overrides["dashboard_password_hash"] = hash_password(v)
                changed.add("dashboard_password_hash")
                continue
            overrides[k] = v
            changed.add(k)

        self.db.set_state(_OVERRIDE_KEY, overrides)
        prev_running = self.engine.running if self.engine else False
        self.cfg = self._build_config(get_settings(), overrides)

        # Selective rebuild to preserve positions where possible.
        if changed & _BROKER_KEYS:
            self.engine.broker = self._make_broker()
            self.engine.data = self._make_data()
        if changed & _AI_KEYS:
            self.engine.strategy = self._make_strategy()
            self.engine.analyst = self._make_analyst()
        if changed & _RISK_KEYS:
            self.engine.risk.max_trade_value = self.cfg.max_trade_value
            self.engine.risk.max_open_positions = self.cfg.max_open_positions
            self.engine.risk.daily_loss_limit = self.cfg.daily_loss_limit
            self.engine.risk.stop_loss_pct = self.cfg.stop_loss_pct
            self.engine.risk.take_profit_pct = self.cfg.take_profit_pct
        self.engine.settings = self.cfg
        self.engine.running = prev_running
        return self.safe_config()

    def safe_config(self) -> dict:
        """Config for the UI — secrets reduced to set/not-set booleans."""
        c = self.cfg
        return {
            "mode": c.mode,
            "effective_mode": c.effective_mode,
            "broker": c.broker,
            "symbols": c.symbols,
            "strategy": c.strategy,
            "loop_interval_seconds": c.loop_interval_seconds,
            "paper_data_source": c.paper_data_source,
            "starting_cash": c.starting_cash,
            "max_trade_value": c.max_trade_value,
            "max_open_positions": c.max_open_positions,
            "daily_loss_limit": c.daily_loss_limit,
            "stop_loss_pct": c.stop_loss_pct,
            "take_profit_pct": c.take_profit_pct,
            "claude_decision_interval": c.claude_decision_interval,
            "dhan_client_id": c.dhan_client_id,
            "security_map": c.security_map,
            "anthropic_model": c.anthropic_model,
            "dashboard_user": c.dashboard_user,
            "has_dhan_token": bool(c.dhan_access_token),
            "has_anthropic_key": bool(c.anthropic_api_key),
            "live_ready": c.live_ready,
        }


def _parse_security_map(raw: str) -> dict:
    import json

    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}


runtime = _Runtime()
