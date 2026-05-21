"""5-indicator weighted scoring strategy.

Combines EMA crossover, RSI, MACD, Supertrend, and momentum into ``buy_score``
and ``sell_score`` (each 0-100), then applies the composite decision rule from
the spec. Pure computation — no I/O, no broker calls — so it is unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import pandas as pd

from app import indicators

# Indicator weights (sum to 100) per the build spec.
WEIGHT_EMA = 20.0
WEIGHT_RSI = 20.0
WEIGHT_MACD = 20.0
WEIGHT_SUPERTREND = 25.0
WEIGHT_MOMENTUM = 15.0

BUY = "BUY"
SELL = "SELL"
HOLD = "HOLD"


@dataclass
class StrategyResult:
    """Outcome of evaluating the strategy on one symbol's candles.

    Attributes:
        decision: ``BUY``, ``SELL`` or ``HOLD``.
        buy_score: Sum of weights of indicators signalling BUY (0-100).
        sell_score: Sum of weights of indicators signalling SELL (0-100).
        confidence: The winning side's score (0-100).
        last_price: Most recent close.
        atr: Most recent ATR(14) value (for position sizing / stops).
        indicators: Per-indicator signal breakdown for logging.
    """

    decision: str
    buy_score: float
    sell_score: float
    confidence: float
    last_price: float
    atr: float
    indicators: Dict[str, str] = field(default_factory=dict)


def _signal_ema(df: pd.DataFrame) -> str:
    ema9 = indicators.ema(df["close"], 9).iloc[-1]
    ema21 = indicators.ema(df["close"], 21).iloc[-1]
    if ema9 > ema21:
        return BUY
    if ema9 < ema21:
        return SELL
    return HOLD


def _signal_rsi(df: pd.DataFrame) -> str:
    value = indicators.rsi(df["close"], 14).iloc[-1]
    if pd.isna(value):
        return HOLD
    if value < 30:
        return BUY
    if value > 70:
        return SELL
    return HOLD


def _signal_macd(df: pd.DataFrame) -> str:
    m = indicators.macd(df["close"])
    macd_line = m["macd"].iloc[-1]
    signal_line = m["signal"].iloc[-1]
    if macd_line > signal_line and macd_line > 0:
        return BUY
    if macd_line < signal_line and macd_line < 0:
        return SELL
    return HOLD


def _signal_supertrend(df: pd.DataFrame) -> str:
    st = indicators.supertrend(df, 10, 3.0)
    direction = st["direction"].iloc[-1]
    return BUY if direction == 1 else SELL


def _signal_momentum(df: pd.DataFrame) -> str:
    value = indicators.momentum(df["close"], 10).iloc[-1]
    if pd.isna(value):
        return HOLD
    if value > 0:
        return BUY
    if value < 0:
        return SELL
    return HOLD


def evaluate(df: pd.DataFrame, min_confidence: float = 60.0) -> StrategyResult:
    """Evaluate the weighted strategy on a candle DataFrame.

    Args:
        df: DataFrame with ``open, high, low, close, volume`` columns,
            oldest-first, with enough rows for the indicators (>= ~35).
        min_confidence: Threshold (0-100) the winning score must meet for a
            non-HOLD decision.

    Returns:
        StrategyResult: The decision and supporting scores/indicators.

    Raises:
        ValueError: If required columns are missing or there are too few rows.
    """
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        raise ValueError(f"df missing columns: {required - set(df.columns)}")
    if len(df) < 35:
        raise ValueError(f"need >=35 candles, got {len(df)}")

    signals = {
        "ema": (_signal_ema(df), WEIGHT_EMA),
        "rsi": (_signal_rsi(df), WEIGHT_RSI),
        "macd": (_signal_macd(df), WEIGHT_MACD),
        "supertrend": (_signal_supertrend(df), WEIGHT_SUPERTREND),
        "momentum": (_signal_momentum(df), WEIGHT_MOMENTUM),
    }

    buy_score = sum(w for sig, w in signals.values() if sig == BUY)
    sell_score = sum(w for sig, w in signals.values() if sig == SELL)

    if buy_score >= min_confidence and buy_score > sell_score:
        decision, confidence = BUY, buy_score
    elif sell_score >= min_confidence and sell_score > buy_score:
        decision, confidence = SELL, sell_score
    else:
        decision, confidence = HOLD, max(buy_score, sell_score)

    last_price = float(df["close"].iloc[-1])
    atr_value = indicators.atr(df, 14).iloc[-1]
    atr_value = float(atr_value) if pd.notna(atr_value) else 0.0

    return StrategyResult(
        decision=decision,
        buy_score=buy_score,
        sell_score=sell_score,
        confidence=confidence,
        last_price=last_price,
        atr=atr_value,
        indicators={name: sig for name, (sig, _w) in signals.items()},
    )
