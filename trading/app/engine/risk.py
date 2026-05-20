"""RiskManager — the hard guardrails that sit between a strategy signal and a
real order. Every protective limit lives here so it is enforced identically in
paper and live mode.

Checks, in order:
  * kill switch / daily-halt state
  * daily loss limit (halts the bot for the rest of the day)
  * max open positions
  * per-trade rupee cap -> position sizing
  * stop-loss / take-profit on open positions (forces an exit signal)
"""
from __future__ import annotations

from dataclasses import dataclass

from ..models import Position, Side, Signal


@dataclass
class RiskDecision:
    approved: bool
    qty: int = 0
    reason: str = ""


class RiskManager:
    def __init__(
        self,
        max_trade_value: float,
        max_open_positions: int,
        daily_loss_limit: float,
        stop_loss_pct: float,
        take_profit_pct: float,
    ):
        self.max_trade_value = max_trade_value
        self.max_open_positions = max_open_positions
        self.daily_loss_limit = daily_loss_limit
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

        self.day_realized_pnl: float = 0.0
        self.halted_for_day: bool = False
        self.kill_switch: bool = False

    # --- lifecycle -------------------------------------------------------
    def start_new_day(self) -> None:
        self.day_realized_pnl = 0.0
        self.halted_for_day = False

    def register_realized_pnl(self, pnl: float) -> None:
        self.day_realized_pnl += pnl
        if self.day_realized_pnl <= -abs(self.daily_loss_limit):
            self.halted_for_day = True

    @property
    def trading_blocked(self) -> bool:
        return self.kill_switch or self.halted_for_day

    def block_reason(self) -> str:
        if self.kill_switch:
            return "kill switch engaged"
        if self.halted_for_day:
            return f"daily loss limit hit ({self.day_realized_pnl:.0f})"
        return ""

    # --- protective exits ------------------------------------------------
    def protective_exit(self, pos: Position) -> Signal | None:
        """Force a SELL if a position breaches stop-loss or take-profit."""
        if pos.avg_price <= 0 or pos.last_price <= 0:
            return None
        change = (pos.last_price - pos.avg_price) / pos.avg_price
        if change <= -self.stop_loss_pct:
            return Signal(pos.symbol, Side.SELL, reason=f"stop-loss hit ({change*100:.1f}%)")
        if change >= self.take_profit_pct:
            return Signal(pos.symbol, Side.SELL, reason=f"take-profit hit ({change*100:.1f}%)")
        return None

    # --- entry sizing & approval ----------------------------------------
    def evaluate_entry(
        self, price: float, cash: float, open_positions: int
    ) -> RiskDecision:
        if self.trading_blocked:
            return RiskDecision(False, reason=self.block_reason())
        if open_positions >= self.max_open_positions:
            return RiskDecision(False, reason="max open positions reached")
        if price <= 0:
            return RiskDecision(False, reason="bad price")

        budget = min(self.max_trade_value, cash)
        qty = int(budget // price)
        if qty < 1:
            return RiskDecision(False, reason="trade budget too small for 1 share")
        return RiskDecision(True, qty=qty, reason="approved")
