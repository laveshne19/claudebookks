from app.engine.risk import RiskManager
from app.models import Position, Side


def make_risk(**kw):
    defaults = dict(
        max_trade_value=5_000,
        max_open_positions=3,
        daily_loss_limit=2_000,
        stop_loss_pct=0.015,
        take_profit_pct=0.03,
    )
    defaults.update(kw)
    return RiskManager(**defaults)


def test_position_sizing_respects_trade_cap():
    r = make_risk(max_trade_value=5_000)
    d = r.evaluate_entry(price=2900, cash=100_000, open_positions=0)
    assert d.approved
    assert d.qty == 1  # 5000 // 2900


def test_position_sizing_limited_by_cash():
    r = make_risk(max_trade_value=50_000)
    d = r.evaluate_entry(price=1000, cash=3_500, open_positions=0)
    assert d.approved and d.qty == 3


def test_max_open_positions_blocks_entry():
    r = make_risk(max_open_positions=2)
    d = r.evaluate_entry(price=100, cash=100_000, open_positions=2)
    assert not d.approved
    assert "max open" in d.reason


def test_daily_loss_limit_halts():
    r = make_risk(daily_loss_limit=2_000)
    r.register_realized_pnl(-1_500)
    assert not r.halted_for_day
    r.register_realized_pnl(-600)
    assert r.halted_for_day
    assert r.trading_blocked
    d = r.evaluate_entry(price=100, cash=100_000, open_positions=0)
    assert not d.approved


def test_kill_switch_blocks():
    r = make_risk()
    r.kill_switch = True
    assert r.trading_blocked
    assert r.evaluate_entry(100, 100_000, 0).approved is False


def test_stop_loss_triggers_exit():
    r = make_risk(stop_loss_pct=0.015)
    pos = Position("RELIANCE", qty=10, avg_price=1000, last_price=980)  # -2%
    sig = r.protective_exit(pos)
    assert sig is not None and sig.side is Side.SELL and "stop-loss" in sig.reason


def test_take_profit_triggers_exit():
    r = make_risk(take_profit_pct=0.03)
    pos = Position("RELIANCE", qty=10, avg_price=1000, last_price=1031)  # +3.1%
    sig = r.protective_exit(pos)
    assert sig is not None and sig.side is Side.SELL and "take-profit" in sig.reason


def test_no_exit_within_band():
    r = make_risk(stop_loss_pct=0.015, take_profit_pct=0.03)
    pos = Position("RELIANCE", qty=10, avg_price=1000, last_price=1005)
    assert r.protective_exit(pos) is None
