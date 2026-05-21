"""Risk management: position sizing, stop-loss math, and the kill switch.

Pure, deterministic functions plus a :class:`RiskManager` that reads/writes the
SQLite state needed to enforce the spec's safety rules:

- Daily loss > 5% of capital -> stop trading for the day.
- 3 consecutive losing trades -> halve position size.
- >= 5 open positions -> no new trades.
- After 15:00 IST -> no new entries (handled via :mod:`app.market`).
- Max risk per trade: 2%.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app import database, market

logger = logging.getLogger(__name__)

KILL_SWITCH_KEY = "kill_switch_triggered"
KILL_SWITCH_DATE_KEY = "kill_switch_date"


def calculate_position_size(price: float, atr: float, capital: float,
                            risk_pct: float = 2.0,
                            size_multiplier: float = 1.0) -> int:
    """Compute share quantity from ATR-based risk and capital caps.

    Risk per trade is capped at ``risk_pct`` of capital (max 2%). Stop distance
    is ``2 * atr``. The result is also capped so no single trade deploys more
    than 10% of capital.

    Args:
        price: Entry price per share (> 0).
        atr: Average True Range used for stop distance (> 0).
        capital: Total trading capital.
        risk_pct: Percent of capital to risk; clamped to <= 2.0.
        size_multiplier: Scaling factor (e.g. 0.5 after a losing streak).

    Returns:
        int: Share quantity (>= 0). Returns 0 when inputs make sizing invalid.
    """
    if price <= 0 or atr <= 0 or capital <= 0:
        return 0
    risk_pct = min(risk_pct, 2.0)
    if risk_pct <= 0:
        return 0

    stop_loss_distance = 2.0 * atr
    risk_amount = capital * (risk_pct / 100.0)
    quantity = int(risk_amount / stop_loss_distance)

    max_qty_by_capital = int((capital * 0.1) / price)
    quantity = min(quantity, max_qty_by_capital)

    quantity = int(quantity * size_multiplier)
    return max(quantity, 0)


def calculate_stop_loss(entry_price: float, atr: float, action: str) -> float:
    """Initial stop-loss price: 2*ATR below (BUY) or above (SELL) entry.

    Args:
        entry_price: Fill price.
        atr: ATR value.
        action: ``BUY`` or ``SELL``.

    Returns:
        float: The stop-loss price.
    """
    distance = 2.0 * atr
    return entry_price - distance if action == "BUY" else entry_price + distance


def trailing_stop_loss(entry_price: float, current_price: float, atr: float,
                       action: str, current_sl: float) -> float:
    """Update a trailing stop.

    Moves the stop to breakeven once price has moved 1*ATR in favour, then
    trails by 1.5*ATR. Never loosens an existing stop.

    Args:
        entry_price: Original entry price.
        current_price: Latest price.
        atr: ATR value.
        action: ``BUY`` or ``SELL``.
        current_sl: The currently active stop-loss price.

    Returns:
        float: The (possibly tightened) stop-loss price.
    """
    if action == "BUY":
        profit = current_price - entry_price
        if profit >= atr:
            new_sl = max(entry_price, current_price - 1.5 * atr)
            return max(current_sl, new_sl)
        return current_sl
    # SELL (short)
    profit = entry_price - current_price
    if profit >= atr:
        new_sl = min(entry_price, current_price + 1.5 * atr)
        return min(current_sl, new_sl)
    return current_sl


@dataclass
class RiskDecision:
    """Whether a new trade may proceed, and why not if blocked."""

    allowed: bool
    reason: str = ""


class RiskManager:
    """Stateful enforcement of trading risk limits backed by SQLite.

    Args:
        capital: Total trading capital.
        daily_loss_limit_pct: Daily loss cap as a percent of capital.
        max_open_positions: Hard cap on concurrently open positions.
        db_path: Optional explicit DB path.
    """

    def __init__(self, capital: float, daily_loss_limit_pct: float = 5.0,
                 max_open_positions: int = 5, db_path: Optional[Path] = None) -> None:
        self.capital = capital
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_open_positions = max_open_positions
        self.db_path = db_path

    # -- Kill switch --------------------------------------------------------

    def _today_str(self) -> str:
        return market.now_ist().date().isoformat()

    def is_kill_switch_active(self) -> bool:
        """Return True if the kill switch is set for the current trading day."""
        triggered = database.get_state(KILL_SWITCH_KEY, "0", self.db_path)
        if triggered != "1":
            return False
        # Kill switch only applies to the day it was triggered; it auto-clears
        # on a new day (user must still restart per spec, but state resets).
        when = database.get_state(KILL_SWITCH_DATE_KEY, "", self.db_path)
        if when != self._today_str():
            self.reset_kill_switch()
            return False
        return True

    def trigger_kill_switch(self, reason: str) -> None:
        """Activate the kill switch for today and log the reason."""
        database.set_state(KILL_SWITCH_KEY, "1", self.db_path)
        database.set_state(KILL_SWITCH_DATE_KEY, self._today_str(), self.db_path)
        logger.warning("KILL SWITCH TRIGGERED: %s", reason)

    def reset_kill_switch(self) -> None:
        """Clear the kill switch (e.g. on a new trading day or manual restart)."""
        database.set_state(KILL_SWITCH_KEY, "0", self.db_path)

    # -- Daily P&L ----------------------------------------------------------

    def realized_pnl_today(self) -> float:
        """Sum realized P&L from trades closed today (IST)."""
        today = self._today_str()
        with database.get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(pnl), 0) AS total FROM trades "
                "WHERE status = 'CLOSED' AND DATE(timestamp) = ?",
                (today,),
            ).fetchone()
        return float(row["total"]) if row else 0.0

    def open_positions_count(self) -> int:
        """Count currently open positions recorded in the DB."""
        with database.get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM trades WHERE status = 'OPEN'"
            ).fetchone()
        return int(row["n"]) if row else 0

    def consecutive_losses(self) -> int:
        """Count consecutive losing closed trades from most recent backwards."""
        with database.get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT pnl FROM trades WHERE status = 'CLOSED' "
                "ORDER BY id DESC LIMIT 20"
            ).fetchall()
        streak = 0
        for r in rows:
            if r["pnl"] is not None and r["pnl"] < 0:
                streak += 1
            else:
                break
        return streak

    def size_multiplier(self) -> float:
        """Return position-size multiplier (0.5 after >=3 consecutive losses)."""
        return 0.5 if self.consecutive_losses() >= 3 else 1.0

    # -- Gate ---------------------------------------------------------------

    def check_daily_loss(self) -> bool:
        """Trigger the kill switch if today's loss exceeds the limit.

        Returns:
            bool: True if the kill switch is (now) active.
        """
        limit = -abs(self.capital * (self.daily_loss_limit_pct / 100.0))
        if self.realized_pnl_today() <= limit:
            if not self.is_kill_switch_active():
                self.trigger_kill_switch(
                    f"Daily loss limit hit: pnl={self.realized_pnl_today():.2f} "
                    f"<= limit={limit:.2f}"
                )
            return True
        return False

    def can_trade(self, when: Optional[dt.datetime] = None) -> RiskDecision:
        """Evaluate all gates for opening a NEW position.

        Args:
            when: Optional datetime for time-based checks; defaults to now IST.

        Returns:
            RiskDecision: ``allowed`` plus a human-readable ``reason`` if blocked.
        """
        if not market.is_market_open(when):
            return RiskDecision(False, "market closed")
        if not market.can_open_new_position(when):
            return RiskDecision(False, "after 15:00 IST new-entry cutoff")
        if self.check_daily_loss() or self.is_kill_switch_active():
            return RiskDecision(False, "kill switch active (daily loss limit)")
        if self.open_positions_count() >= self.max_open_positions:
            return RiskDecision(False, "max open positions reached")
        return RiskDecision(True, "")
