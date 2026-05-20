"""Strategy interface. A strategy is pure: given price history it returns a
Signal. It never places orders or knows about brokers — that keeps strategies
easy to test and reason about.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Signal


class Strategy(ABC):
    name: str = "base"
    # Minimum number of closing prices needed before the strategy will act.
    warmup: int = 1

    @abstractmethod
    def evaluate(self, symbol: str, closes: list[float], holding: bool) -> Signal:
        """Return a Signal for one symbol.

        `holding` indicates whether we currently hold an open long position,
        so the strategy can decide between entry and exit logic.
        """
