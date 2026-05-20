import os
import tempfile

from app.brokers.paper import PaperBroker
from app.config import Settings
from app.db import Database
from app.engine.risk import RiskManager
from app.engine.trader import TradingEngine, market_is_open
from app.market.data import SyntheticData
from app.strategy.sma_crossover import SmaCrossover
from datetime import datetime
from zoneinfo import ZoneInfo


def build_engine():
    settings = Settings()
    settings.symbols = ["RELIANCE", "TCS", "INFY"]
    db = Database(os.path.join(tempfile.mkdtemp(), "t.db"))
    broker = PaperBroker(settings.starting_cash)
    risk = RiskManager(
        max_trade_value=settings.max_trade_value,
        max_open_positions=settings.max_open_positions,
        daily_loss_limit=settings.daily_loss_limit,
        stop_loss_pct=settings.stop_loss_pct,
        take_profit_pct=settings.take_profit_pct,
    )
    engine = TradingEngine(
        broker=broker,
        data_provider=SyntheticData(settings.symbols),
        strategy=SmaCrossover(fast=3, slow=5),
        risk=risk,
        db=db,
        settings=settings,
    )
    return engine


def test_market_hours_weekend_closed():
    sat = datetime(2026, 5, 23, 11, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    assert market_is_open(sat) is False


def test_market_hours_weekday_open():
    wed = datetime(2026, 5, 20, 11, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    assert market_is_open(wed) is True


def test_forced_loop_runs_and_snapshots_equity():
    engine = build_engine()
    engine.start()
    result = engine.run_once(force=True)
    assert "note" in result
    # equity snapshot recorded
    assert len(engine.db.equity_curve()) >= 1
    status = engine.status()
    assert status["mode"] == "paper"
    assert status["equity"] > 0


def test_panic_flatten_engages_kill_switch():
    engine = build_engine()
    engine.start()
    # force a buy by directly placing through broker, then panic
    engine.broker.place_order("RELIANCE", __import__("app.models", fromlist=["Side"]).Side.BUY, 1, 2900, "manual")
    closed = engine.panic_flatten()
    assert engine.risk.kill_switch is True
    assert engine.running is False
    assert closed >= 1
    assert len(engine.broker.positions()) == 0


def test_stopped_engine_does_nothing():
    engine = build_engine()
    engine.stop()
    result = engine.run_once()
    assert result["note"] == "stopped"
