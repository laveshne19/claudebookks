"""TradingEngine — orchestrates one decision loop:

  1. pull quotes -> update price history + mark open positions
  2. for each open position, check protective stop-loss/take-profit exits
  3. for each symbol, ask the strategy for a signal
  4. run signals through the RiskManager (sizing + approval)
  5. place approved orders via the active broker, log every fill/rejection
  6. snapshot equity for the dashboard chart

The loop is driven by APScheduler in main.py; this class is sync and testable
in isolation.
"""
from __future__ import annotations

import threading
from datetime import datetime, time
from zoneinfo import ZoneInfo

from ..db import Database
from ..models import OrderStatus, Side, now_iso
from .risk import RiskManager

IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


def market_is_open(dt: datetime | None = None) -> bool:
    dt = dt or datetime.now(IST)
    if dt.weekday() >= 5:  # Sat/Sun
        return False
    return MARKET_OPEN <= dt.time() <= MARKET_CLOSE


class TradingEngine:
    def __init__(self, *, broker, data_provider, strategy, risk: RiskManager, db: Database, settings):
        self.broker = broker
        self.data = data_provider
        self.strategy = strategy
        self.risk = risk
        self.db = db
        self.settings = settings

        self.running: bool = False
        self.respect_market_hours: bool = True
        self._lock = threading.Lock()
        self._last_quotes: dict[str, float] = {}
        self._day = datetime.now(IST).date()
        self.last_loop_ts: str = ""
        self.last_loop_note: str = "idle"

    # --- controls --------------------------------------------------------
    def start(self) -> None:
        self.running = True
        self.risk.kill_switch = False

    def stop(self) -> None:
        self.running = False

    def panic_flatten(self) -> int:
        """Immediately close every open position and engage the kill switch."""
        with self._lock:
            closed = 0
            for pos in list(self.broker.positions()):
                price = self._last_quotes.get(pos.symbol, pos.last_price or pos.avg_price)
                self._execute(pos.symbol, Side.SELL, pos.qty, price, "PANIC flatten")
                closed += 1
            self.risk.kill_switch = True
            self.running = False
            return closed

    # --- main loop -------------------------------------------------------
    def run_once(self, force: bool = False) -> dict:
        with self._lock:
            return self._run_once_locked(force)

    def _run_once_locked(self, force: bool) -> dict:
        self.last_loop_ts = now_iso()

        today = datetime.now(IST).date()
        if today != self._day:
            self._day = today
            self.risk.start_new_day()

        if not self.running and not force:
            self.last_loop_note = "stopped"
            return {"note": "stopped"}

        if self.respect_market_hours and not market_is_open() and not force:
            self.last_loop_note = "market closed"
            self._snapshot_equity()
            return {"note": "market closed"}

        quotes = self.data.quotes(self.settings.symbols)
        prices = {s: q.ltp for s, q in quotes.items()}
        self._last_quotes.update(prices)
        self.broker.mark_prices(prices)

        actions: list[dict] = []
        held = {p.symbol: p for p in self.broker.positions()}

        # 1) protective exits first
        for sym, pos in list(held.items()):
            exit_sig = self.risk.protective_exit(pos)
            if exit_sig is not None:
                price = prices.get(sym, pos.last_price)
                res = self._execute(sym, Side.SELL, pos.qty, price, exit_sig.reason)
                actions.append(res)
                held.pop(sym, None)

        # 2) strategy signals
        if not self.risk.trading_blocked:
            for sym in self.settings.symbols:
                closes = self.data.history.closes(sym)
                holding = sym in held
                sig = self.strategy.evaluate(sym, closes, holding)
                if sig.side is None:
                    continue
                price = prices.get(sym)
                if not price:
                    continue

                if sig.side is Side.BUY:
                    decision = self.risk.evaluate_entry(price, self.broker.cash(), len(held))
                    if not decision.approved:
                        continue
                    res = self._execute(sym, Side.BUY, decision.qty, price, sig.reason)
                    if res["status"] == OrderStatus.FILLED.value:
                        held[sym] = True  # mark slot used
                    actions.append(res)
                elif sig.side is Side.SELL and holding:
                    pos = self.broker.positions()
                    qty = next((p.qty for p in pos if p.symbol == sym), 0)
                    if qty > 0:
                        res = self._execute(sym, Side.SELL, qty, price, sig.reason)
                        actions.append(res)
                        held.pop(sym, None)

        self._snapshot_equity()
        self.last_loop_note = f"{len(actions)} action(s)" if actions else "no action"
        return {"note": self.last_loop_note, "actions": actions, "quotes": prices}

    # --- helpers ---------------------------------------------------------
    def _execute(self, symbol: str, side: Side, qty: int, price: float, reason: str) -> dict:
        order = self.broker.place_order(symbol, side, qty, price, reason)
        realized = getattr(self.broker, "last_realized_pnl", 0.0) if side is Side.SELL else 0.0
        if order.status is OrderStatus.FILLED and side is Side.SELL:
            self.risk.register_realized_pnl(realized)
        self.db.record_trade(order, self.settings.effective_mode, realized)
        return {**order.to_dict(), "realized_pnl": round(realized, 2)}

    def equity(self) -> float:
        positions_value = sum(p.market_value for p in self.broker.positions())
        return self.broker.cash() + positions_value

    def _snapshot_equity(self) -> None:
        eq = self.equity()
        self.db.record_equity(now_iso(), round(eq, 2), round(self.broker.cash(), 2), round(self.risk.day_realized_pnl, 2))

    def status(self) -> dict:
        return {
            "running": self.running,
            "mode": self.settings.effective_mode,
            "requested_mode": self.settings.mode,
            "broker": self.broker.name,
            "data_source": self.data.name,
            "market_open": market_is_open(),
            "respect_market_hours": self.respect_market_hours,
            "kill_switch": self.risk.kill_switch,
            "halted_for_day": self.risk.halted_for_day,
            "block_reason": self.risk.block_reason(),
            "cash": round(self.broker.cash(), 2),
            "equity": round(self.equity(), 2),
            "day_realized_pnl": round(self.risk.day_realized_pnl, 2),
            "open_positions": [p.to_dict() for p in self.broker.positions()],
            "last_loop_ts": self.last_loop_ts,
            "last_loop_note": self.last_loop_note,
            "strategy": self.strategy.name,
            "symbols": self.settings.symbols,
            "limits": {
                "max_trade_value": self.settings.max_trade_value,
                "max_open_positions": self.settings.max_open_positions,
                "daily_loss_limit": self.settings.daily_loss_limit,
                "stop_loss_pct": self.settings.stop_loss_pct,
                "take_profit_pct": self.settings.take_profit_pct,
            },
        }
