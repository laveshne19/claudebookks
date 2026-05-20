from __future__ import annotations

from .base import Strategy
from .sma_crossover import SmaCrossover

_STRATEGIES: dict[str, type[Strategy]] = {
    SmaCrossover.name: SmaCrossover,
}


def get_strategy(name: str) -> Strategy:
    cls = _STRATEGIES.get(name, SmaCrossover)
    return cls()


def available() -> list[str]:
    # claude_advisor is constructed separately (needs API key) but is selectable.
    return list(_STRATEGIES.keys()) + ["claude_advisor"]
