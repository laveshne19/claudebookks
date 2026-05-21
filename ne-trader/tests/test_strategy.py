"""Unit tests for the weighted scoring strategy."""

import pandas as pd
import pytest

from app import strategy


def _ramp_df(start: float, step: float, n: int = 60) -> pd.DataFrame:
    close = pd.Series([start + step * i for i in range(n)], dtype=float)
    return pd.DataFrame({
        "open": close,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": pd.Series([1000] * n, dtype=float),
    })


def test_uptrend_yields_buy():
    # Trend indicators (EMA, MACD, Supertrend, Momentum = 80) signal BUY;
    # RSI is overbought and signals SELL (20). Net decision: BUY @ 80%.
    result = strategy.evaluate(_ramp_df(100, 1.0), min_confidence=60.0)
    assert result.decision == strategy.BUY
    assert result.buy_score == pytest.approx(80.0)
    assert result.sell_score == pytest.approx(20.0)
    assert result.confidence == pytest.approx(80.0)
    assert result.atr > 0


def test_downtrend_yields_sell():
    result = strategy.evaluate(_ramp_df(300, -1.0), min_confidence=60.0)
    assert result.decision == strategy.SELL
    assert result.sell_score == pytest.approx(80.0)
    assert result.buy_score == pytest.approx(20.0)


def test_high_threshold_forces_hold():
    # With a 90% threshold, the 80% buy score is not enough -> HOLD.
    result = strategy.evaluate(_ramp_df(100, 1.0), min_confidence=90.0)
    assert result.decision == strategy.HOLD


def test_requires_minimum_candles():
    with pytest.raises(ValueError):
        strategy.evaluate(_ramp_df(100, 1.0, n=10))


def test_missing_columns_raises():
    df = pd.DataFrame({"close": list(range(40))})
    with pytest.raises(ValueError):
        strategy.evaluate(df)
