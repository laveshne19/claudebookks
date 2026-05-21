"""Unit tests for position sizing, stops, and the kill switch."""

import pytest

from app import database, market, risk_manager
from app.risk_manager import (RiskManager, calculate_position_size,
                              calculate_stop_loss, trailing_stop_loss)


# -- Position sizing --------------------------------------------------------

def test_position_size_normal_capped_by_capital():
    # risk_amount=2000, stop_dist=4 -> 500 by risk; capped by 10% capital/price
    # = (100000*0.1)/100 = 100.
    assert calculate_position_size(price=100, atr=2, capital=100000,
                                   risk_pct=2.0) == 100


def test_position_size_zero_capital():
    assert calculate_position_size(price=100, atr=2, capital=0) == 0


def test_position_size_huge_atr_is_zero():
    assert calculate_position_size(price=100, atr=100000, capital=100000,
                                   risk_pct=2.0) == 0


def test_position_size_risk_pct_clamped_to_two():
    # Even if 10% is requested, sizing must use the 2% max.
    capped = calculate_position_size(price=100, atr=2, capital=100000, risk_pct=10)
    at_two = calculate_position_size(price=100, atr=2, capital=100000, risk_pct=2)
    assert capped == at_two


def test_position_size_multiplier_halves():
    full = calculate_position_size(price=100, atr=20, capital=100000, risk_pct=2.0)
    half = calculate_position_size(price=100, atr=20, capital=100000, risk_pct=2.0,
                                   size_multiplier=0.5)
    assert half == full // 2


def test_stop_loss_directions():
    assert calculate_stop_loss(100, 2, "BUY") == pytest.approx(96.0)
    assert calculate_stop_loss(100, 2, "SELL") == pytest.approx(104.0)


def test_trailing_moves_to_profit_for_buy():
    # Entry 100, price moved +5 with ATR 2 (>=1 ATR profit) -> SL trails up.
    new_sl = trailing_stop_loss(entry_price=100, current_price=105, atr=2,
                                action="BUY", current_sl=96)
    assert new_sl > 96
    assert new_sl >= 100  # at least breakeven


def test_trailing_never_loosens():
    new_sl = trailing_stop_loss(entry_price=100, current_price=101, atr=2,
                                action="BUY", current_sl=99)
    assert new_sl == 99  # profit < 1 ATR, unchanged


# -- Kill switch (DB-backed) ------------------------------------------------

def _insert_closed_trade(db_path, pnl: float) -> None:
    ts = market.now_ist().isoformat()
    with database.get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO trades(timestamp, symbol, exchange, segment, action, "
            "quantity, entry_price, status, paper_mode, pnl) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (ts, "TEST", "NSE", "EQ", "BUY", 1, 100.0, "CLOSED", 1, pnl),
        )
        conn.commit()


@pytest.fixture()
def tmp_db(tmp_path):
    db = tmp_path / "trader.db"
    database.init_db(db)
    return db


def test_daily_loss_triggers_kill_switch(tmp_db):
    rm = RiskManager(capital=100000, daily_loss_limit_pct=5.0, db_path=tmp_db)
    assert not rm.is_kill_switch_active()
    _insert_closed_trade(tmp_db, -6000.0)  # > 5% of 100000
    assert rm.check_daily_loss() is True
    assert rm.is_kill_switch_active() is True


def test_under_limit_does_not_trigger(tmp_db):
    rm = RiskManager(capital=100000, daily_loss_limit_pct=5.0, db_path=tmp_db)
    _insert_closed_trade(tmp_db, -1000.0)
    assert rm.check_daily_loss() is False
    assert not rm.is_kill_switch_active()


def test_consecutive_losses_reduce_size(tmp_db):
    rm = RiskManager(capital=100000, db_path=tmp_db)
    for _ in range(3):
        _insert_closed_trade(tmp_db, -100.0)
    assert rm.consecutive_losses() == 3
    assert rm.size_multiplier() == 0.5


def test_winning_trade_breaks_loss_streak(tmp_db):
    rm = RiskManager(capital=100000, db_path=tmp_db)
    _insert_closed_trade(tmp_db, -100.0)
    _insert_closed_trade(tmp_db, -100.0)
    _insert_closed_trade(tmp_db, 50.0)  # most recent is a win
    assert rm.consecutive_losses() == 0
    assert rm.size_multiplier() == 1.0


def test_max_open_positions_blocks(tmp_db):
    rm = RiskManager(capital=100000, max_open_positions=2, db_path=tmp_db)
    with database.get_connection(tmp_db) as conn:
        for _ in range(2):
            conn.execute(
                "INSERT INTO trades(symbol, exchange, segment, action, quantity, "
                "entry_price, status, paper_mode) VALUES(?,?,?,?,?,?,?,?)",
                ("X", "NSE", "EQ", "BUY", 1, 100.0, "OPEN", 1))
        conn.commit()
    assert rm.open_positions_count() == 2
