"""Core domain types shared across brokers, strategy, engine and API."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"


@dataclass
class Quote:
    symbol: str
    ltp: float
    ts: str = field(default_factory=now_iso)


@dataclass
class Order:
    symbol: str
    side: Side
    qty: int
    price: float
    status: OrderStatus = OrderStatus.PENDING
    order_id: str = ""
    reason: str = ""  # strategy / risk rationale, surfaced in the trade log
    ts: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["side"] = self.side.value
        d["status"] = self.status.value
        return d


@dataclass
class Position:
    symbol: str
    qty: int
    avg_price: float
    last_price: float = 0.0
    opened_at: str = field(default_factory=now_iso)

    @property
    def market_value(self) -> float:
        return self.qty * self.last_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.last_price - self.avg_price) * self.qty

    def to_dict(self) -> dict:
        d = asdict(self)
        d["market_value"] = round(self.market_value, 2)
        d["unrealized_pnl"] = round(self.unrealized_pnl, 2)
        return d


@dataclass
class Signal:
    """Output of a strategy for one symbol on one evaluation."""

    symbol: str
    side: Optional[Side]  # None = no action
    reason: str = ""
    strength: float = 0.0  # 0..1, optional confidence
