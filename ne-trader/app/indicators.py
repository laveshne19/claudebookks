"""Pure technical-indicator functions built on pandas/numpy.

Every function is side-effect free and operates on a price/candle Series or
DataFrame, making them trivially unit-testable against known values. Functions
return full Series (aligned to the input index) unless named ``*_latest``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average.

    Args:
        series: Price series (typically close).
        period: EMA span (> 0).

    Returns:
        pandas.Series: EMA values aligned to the input index.

    Raises:
        ValueError: If period <= 0.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing).

    Args:
        series: Price series (close).
        period: Lookback period; defaults to 14.

    Returns:
        pandas.Series: RSI values in [0, 100]. Early values may be NaN.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    # When average loss is zero (pure uptrend), RSI is 100.
    out = out.where(avg_loss != 0.0, 100.0)
    return out


def macd(series: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> pd.DataFrame:
    """Moving Average Convergence Divergence.

    Args:
        series: Price series (close).
        fast: Fast EMA period.
        slow: Slow EMA period.
        signal: Signal-line EMA period.

    Returns:
        pandas.DataFrame: Columns ``macd``, ``signal``, ``hist``.
    """
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range.

    Args:
        df: DataFrame with ``high``, ``low``, ``close`` columns.
        period: Lookback period; defaults to 14.

    Returns:
        pandas.Series: ATR values aligned to the input index.

    Raises:
        ValueError: If required columns are missing.
    """
    required = {"high", "low", "close"}
    if not required.issubset(df.columns):
        raise ValueError(f"df missing columns: {required - set(df.columns)}")
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def supertrend(df: pd.DataFrame, period: int = 10,
               multiplier: float = 3.0) -> pd.DataFrame:
    """Supertrend indicator.

    Args:
        df: DataFrame with ``high``, ``low``, ``close`` columns.
        period: ATR period; defaults to 10.
        multiplier: ATR multiplier; defaults to 3.0.

    Returns:
        pandas.DataFrame: Columns ``supertrend`` (the line) and ``direction``
        (1 = uptrend/price above line, -1 = downtrend).
    """
    required = {"high", "low", "close"}
    if not required.issubset(df.columns):
        raise ValueError(f"df missing columns: {required - set(df.columns)}")

    atr_series = atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2.0
    upper_basic = hl2 + multiplier * atr_series
    lower_basic = hl2 - multiplier * atr_series

    close = df["close"].to_numpy()
    upper = upper_basic.to_numpy()
    lower = lower_basic.to_numpy()
    n = len(df)

    final_upper = np.full(n, np.nan)
    final_lower = np.full(n, np.nan)
    trend = np.ones(n, dtype=int)

    for i in range(n):
        if np.isnan(upper[i]) or np.isnan(lower[i]):
            # ATR warm-up period: no valid bands yet.
            final_upper[i] = np.nan
            final_lower[i] = np.nan
            trend[i] = 1
            continue

        prev_fu = final_upper[i - 1] if i > 0 else np.nan
        prev_fl = final_lower[i - 1] if i > 0 else np.nan

        if np.isnan(prev_fu):
            final_upper[i] = upper[i]
        else:
            final_upper[i] = (upper[i]
                              if (upper[i] < prev_fu or close[i - 1] > prev_fu)
                              else prev_fu)
        if np.isnan(prev_fl):
            final_lower[i] = lower[i]
        else:
            final_lower[i] = (lower[i]
                              if (lower[i] > prev_fl or close[i - 1] < prev_fl)
                              else prev_fl)

        if np.isnan(prev_fu) or np.isnan(prev_fl):
            # First valid bar: seed direction from price vs the band.
            trend[i] = 1 if close[i] >= final_lower[i] else -1
        elif close[i] > prev_fu:
            trend[i] = 1
        elif close[i] < prev_fl:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]

    line = np.where(trend == 1, final_lower, final_upper)
    return pd.DataFrame(
        {"supertrend": line, "direction": trend}, index=df.index
    )


def momentum(series: pd.Series, period: int = 10) -> pd.Series:
    """Price momentum: current close minus close ``period`` bars ago.

    Args:
        series: Price series (close).
        period: Lookback period; defaults to 10.

    Returns:
        pandas.Series: Momentum values (positive = up, negative = down).
    """
    if period <= 0:
        raise ValueError("period must be positive")
    return series - series.shift(period)
