"""Broker abstraction. The engine only ever talks to this interface, so adding
a new broker (Kite, Groww, ...) later means writing one adapter, not rewriting
the engine.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Order, Position, Side


class BrokerAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def cash(self) -> float:
        """Available buying power in rupees."""

    @abstractmethod
    def positions(self) -> list[Position]:
        ...

    @abstractmethod
    def place_order(self, symbol: str, side: Side, qty: int, price: float, reason: str = "") -> Order:
        """Submit an order. Implementations return a filled/rejected Order."""

    @abstractmethod
    def mark_prices(self, prices: dict[str, float]) -> None:
        """Update last-traded prices on open positions (for P&L)."""
