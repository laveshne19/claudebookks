"""Unit tests for the pure indicator functions."""

import numpy as np
import pandas as pd
import pytest

from app import indicators


def _ramp_df(start: float, step: float, n: int = 60) -> pd.DataFrame:
    close = pd.Series([start + step * i for i in range(n)], dtype=float)
    return pd.DataFrame({
        "open": close,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": pd.Series([1000] * n, dtype=float),
    })


def test_ema_constant_series_equals_constant():
    s = pd.Series([50.0] * 30)
    assert indicators.ema(s, 9).iloc[-1] == pytest.approx(50.0)


def test_ema_rejects_nonpositive_period():
    with pytest.raises(ValueError):
        indicators.ema(pd.Series([1.0, 2.0]), 0)


def test_rsi_uptrend_is_overbought():
    s = _ramp_df(100, 1.0)["close"]
    assert indicators.rsi(s, 14).iloc[-1] == pytest.approx(100.0)


def test_rsi_downtrend_is_oversold():
    s = _ramp_df(200, -1.0)["close"]
    assert indicators.rsi(s, 14).iloc[-1] < 5.0


def test_momentum_matches_difference():
    s = _ramp_df(100, 2.0)["close"]
    # 2 per bar over 10 bars = 20.
    assert indicators.momentum(s, 10).iloc[-1] == pytest.approx(20.0)


def test_atr_is_positive():
    df = _ramp_df(100, 1.0)
    assert indicators.atr(df, 14).iloc[-1] > 0


def test_atr_requires_columns():
    with pytest.raises(ValueError):
        indicators.atr(pd.DataFrame({"close": [1, 2, 3]}), 14)


def test_supertrend_direction_up_in_uptrend():
    df = _ramp_df(100, 1.0)
    assert indicators.supertrend(df, 10, 3.0)["direction"].iloc[-1] == 1


def test_supertrend_direction_down_in_downtrend():
    df = _ramp_df(300, -1.0)
    assert indicators.supertrend(df, 10, 3.0)["direction"].iloc[-1] == -1


def test_macd_positive_in_uptrend():
    s = _ramp_df(100, 1.0)["close"]
    m = indicators.macd(s)
    assert m["macd"].iloc[-1] > 0
    assert m["macd"].iloc[-1] > m["signal"].iloc[-1]
