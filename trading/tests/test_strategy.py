from app.models import Side
from app.strategy.indicators import rsi, sma
from app.strategy.sma_crossover import SmaCrossover


def test_sma_and_rsi_basic():
    assert sma([1, 2, 3, 4], 2) == 3.5
    assert sma([1], 2) is None
    # strictly rising series -> RSI 100
    assert rsi(list(range(1, 20)), 14) == 100.0


def test_warmup_returns_no_signal():
    s = SmaCrossover()
    sig = s.evaluate("X", [100, 101], holding=False)
    assert sig.side is None


def test_golden_cross_generates_buy():
    # high overbought so the RSI filter doesn't mask the crossover under test
    s = SmaCrossover(fast=3, slow=5, rsi_period=3, overbought=120)
    # flat, then a jump on the final bar -> fast crosses above slow on the last bar
    closes = [100, 100, 100, 100, 100, 100, 100, 100, 100, 112]
    sig = s.evaluate("X", closes, holding=False)
    assert sig.side is Side.BUY


def test_death_cross_generates_sell_when_holding():
    s = SmaCrossover(fast=3, slow=5, rsi_period=3, overbought=95)
    # flat, then a drop on the final bar -> fast crosses below slow on the last bar
    closes = [100, 100, 100, 100, 100, 100, 100, 100, 100, 88]
    sig = s.evaluate("X", closes, holding=True)
    assert sig.side is Side.SELL
