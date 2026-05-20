"""Paper (simulated) broker. Fills instantly at the requested price, tracks
cash and positions in memory, and computes realized P&L on closes.

This is the default and is what you should run until the strategy is proven.
"""
from __future__ import annotations

import uuid

from ..models import Order, OrderStatus, Position, Side


class PaperBroker:
    name = "paper"

    def __init__(self, starting_cash: float):
        self._cash = starting_cash
        self._positions: dict[str, Position] = {}
        self.last_realized_pnl: float = 0.0

    def cash(self) -> float:
        return self._cash

    def positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_position(self, symbol: str) -> Position | None:
        return self._positions.get(symbol)

    def place_order(self, symbol: str, side: Side, qty: int, price: float, reason: str = "") -> Order:
        self.last_realized_pnl = 0.0
        order = Order(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            order_id=f"paper-{uuid.uuid4().hex[:10]}",
            reason=reason,
        )

        if qty <= 0 or price <= 0:
            order.status = OrderStatus.REJECTED
            order.reason = f"{reason} | invalid qty/price".strip(" |")
            return order

        cost = qty * price
        if side is Side.BUY:
            if cost > self._cash + 1e-6:
                order.status = OrderStatus.REJECTED
                order.reason = f"{reason} | insufficient cash".strip(" |")
                return order
            self._cash -= cost
            existing = self._positions.get(symbol)
            if existing is None:
                self._positions[symbol] = Position(
                    symbol=symbol, qty=qty, avg_price=price, last_price=price
                )
            else:
                total_qty = existing.qty + qty
                existing.avg_price = (
                    existing.avg_price * existing.qty + price * qty
                ) / total_qty
                existing.qty = total_qty
                existing.last_price = price
            order.status = OrderStatus.FILLED
            return order

        # SELL
        existing = self._positions.get(symbol)
        if existing is None or existing.qty < qty:
            order.status = OrderStatus.REJECTED
            order.reason = f"{reason} | no/insufficient position to sell".strip(" |")
            return order

        self.last_realized_pnl = (price - existing.avg_price) * qty
        self._cash += qty * price
        existing.qty -= qty
        existing.last_price = price
        if existing.qty == 0:
            del self._positions[symbol]
        order.status = OrderStatus.FILLED
        return order

    def mark_prices(self, prices: dict[str, float]) -> None:
        for sym, pos in self._positions.items():
            if sym in prices and prices[sym] > 0:
                pos.last_price = prices[sym]
