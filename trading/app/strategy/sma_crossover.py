"""SMA crossover + RSI filter.

Entry (BUY): fast SMA crosses above slow SMA AND RSI < overbought.
Exit (SELL): fast SMA crosses below slow SMA OR RSI > overbought.

A classic, well-understood trend-following baseline. Stop-loss / take-profit
are enforced separately by the RiskManager, not here.
"""
from __future__ import annotations

from ..models import Side, Signal
from .base import Strategy
from .indicators import rsi, sma


class SmaCrossover(Strategy):
    name = "sma_crossover"

    def __init__(self, fast: int = 9, slow: int = 21, rsi_period: int = 14, overbought: float = 70.0):
        self.fast = fast
        self.slow = slow
        self.rsi_period = rsi_period
        self.overbought = overbought
        self.warmup = slow + 1

    def evaluate(self, symbol: str, closes: list[float], holding: bool) -> Signal:
        if len(closes) < self.warmup:
            return Signal(symbol=symbol, side=None, reason="warming up")

        fast_now = sma(closes, self.fast)
        slow_now = sma(closes, self.slow)
        fast_prev = sma(closes[:-1], self.fast)
        slow_prev = sma(closes[:-1], self.slow)
        r = rsi(closes, self.rsi_period) or 50.0

        if None in (fast_now, slow_now, fast_prev, slow_prev):
            return Signal(symbol=symbol, side=None, reason="insufficient data")

        crossed_up = fast_prev <= slow_prev and fast_now > slow_now
        crossed_down = fast_prev >= slow_prev and fast_now < slow_now

        if not holding and crossed_up and r < self.overbought:
            return Signal(
                symbol=symbol,
                side=Side.BUY,
                reason=f"SMA{self.fast} crossed above SMA{self.slow}, RSI={r:.0f}",
                strength=min(1.0, (fast_now - slow_now) / slow_now * 50),
            )

        if holding and (crossed_down or r > self.overbought):
            why = "SMA crossed down" if crossed_down else f"RSI overbought ({r:.0f})"
            return Signal(symbol=symbol, side=Side.SELL, reason=why)

        return Signal(symbol=symbol, side=None, reason="no crossover")
