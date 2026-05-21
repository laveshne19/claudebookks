"""Core scanning and trade-execution loop.

The :class:`Trader` orchestrates one full scan cycle:

1. For each watchlist symbol, fetch candles and evaluate the strategy.
2. Log every scan to ``scan_log`` (whether or not it trades).
3. For qualifying signals, run the risk gate and (optionally) the Claude
   overlay, then open a position.
4. Manage open positions (stop-loss / trailing) and square off at 15:15 IST.

CRITICAL: every execution path checks ``self.cfg.paper_mode``. In paper mode no
broker order is ever placed; trades are simulated and stored with
``paper_mode=1``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from app import database, market, strategy
from app.config import Config
from app.kite_client import KiteAuthError, KiteClient, KiteClientError
from app.risk_manager import (RiskManager, calculate_position_size,
                              calculate_stop_loss, trailing_stop_loss)

logger = logging.getLogger(__name__)


class Trader:
    """Drives scanning and (paper or live) order execution.

    Args:
        cfg: Loaded application config.
        kite: Broker client (may be unauthenticated in pure paper testing).
        claude: Optional Claude overlay client (``None`` disables the overlay).
        db_path: Optional explicit DB path (defaults to ``cfg.db_path``).
    """

    def __init__(self, cfg: Config, kite: KiteClient,
                 claude: Optional[object] = None,
                 db_path: Optional[Path] = None) -> None:
        self.cfg = cfg
        self.kite = kite
        self.claude = claude
        self.db_path = db_path or cfg.db_path
        self.risk = RiskManager(
            capital=cfg.total_capital,
            daily_loss_limit_pct=cfg.daily_loss_limit_pct,
            max_open_positions=cfg.max_open_positions,
            db_path=self.db_path,
        )

    def _effective_paper(self) -> bool:
        """True if trades must be simulated.

        Real orders require BOTH ``LIVE_MODE=true`` in config AND the absence of
        a runtime ``force_paper`` override (set via the dashboard). This makes
        paper the safe default and lets an operator force paper without ever
        being able to flip to live from the UI.
        """
        if self.cfg.paper_mode:
            return True
        return database.get_state("force_paper", "0", self.db_path) == "1"

    # -- Scan ---------------------------------------------------------------

    def scan_once(self) -> None:
        """Run one full scan over the watchlist, opening trades where allowed."""
        if not market.is_market_open():
            logger.info("Market closed; skipping scan")
            return
        database.set_state("last_scan_time", market.now_ist().isoformat(),
                           self.db_path)

        # Manage existing positions first (stops may free up slots).
        self.manage_open_positions()

        if market.is_square_off_time():
            logger.info("Square-off time reached; closing all positions")
            self.square_off_all()
            return

        for symbol in self.cfg.watchlist:
            try:
                self._scan_symbol(symbol)
            except KiteAuthError:
                logger.error("Auth error during scan; aborting cycle")
                database.set_state("token_valid", "0", self.db_path)
                return
            except KiteClientError as exc:
                logger.warning("Skipping %s due to data error: %s", symbol, exc)

    def _scan_symbol(self, symbol: str) -> None:
        df = self.kite.historical_candles(symbol, interval="15minute", count=100)
        result = strategy.evaluate(df, min_confidence=self.cfg.min_confidence)

        claude_used = 0
        decision = result.decision

        if decision in ("BUY", "SELL"):
            gate = self.risk.can_trade()
            if not gate.allowed:
                decision = "HOLD"
                self._log_scan(symbol, result, claude_used, note=gate.reason)
                return

            # Claude overlay (consulted on every qualifying signal per config).
            if self.claude is not None:
                claude_used = 1
                verdict = self._consult_claude(symbol, result, df)
                if verdict == "HOLD":
                    logger.info("Claude overrode %s on %s -> HOLD",
                                result.decision, symbol)
                    self._log_scan(symbol, result, claude_used, note="claude HOLD")
                    return

        self._log_scan(symbol, result, claude_used)

        if decision in ("BUY", "SELL"):
            self._open_position(symbol, result, claude_used)

    def _consult_claude(self, symbol: str, result: strategy.StrategyResult,
                        df) -> str:
        """Ask the Claude overlay for a second opinion; never block on errors."""
        try:
            return self.claude.second_opinion(  # type: ignore[union-attr]
                symbol=symbol, result=result, candles=df,
                open_positions=self.risk.open_positions_count(),
            )
        except Exception as exc:  # noqa: BLE001 - overlay must never block trades
            logger.warning("Claude overlay failed (%s); proceeding rules-only", exc)
            return result.decision

    def _log_scan(self, symbol: str, result: strategy.StrategyResult,
                  claude_used: int, note: str = "") -> None:
        indicators_json = json.dumps({**result.indicators, "note": note})
        with database.get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO scan_log(symbol, decision, buy_score, sell_score, "
                "indicators_json, claude_used) VALUES(?,?,?,?,?,?)",
                (symbol, result.decision, result.buy_score, result.sell_score,
                 indicators_json, claude_used),
            )
            conn.commit()

    # -- Execution ----------------------------------------------------------

    def _open_position(self, symbol: str, result: strategy.StrategyResult,
                       claude_used: int) -> None:
        qty = calculate_position_size(
            price=result.last_price, atr=result.atr,
            capital=self.cfg.total_capital,
            risk_pct=self.cfg.risk_per_trade_pct,
            size_multiplier=self.risk.size_multiplier(),
        )
        if qty <= 0:
            logger.info("Position size 0 for %s; skipping", symbol)
            return

        stop_loss = calculate_stop_loss(result.last_price, result.atr,
                                        result.decision)
        order_id = None
        is_paper = self._effective_paper()
        paper = 1 if is_paper else 0

        if is_paper:
            logger.info("[PAPER] %s %s x%d @ %.2f (conf %.0f%%)",
                        result.decision, symbol, qty, result.last_price,
                        result.confidence)
        else:
            try:
                order_id = self.kite.place_order(
                    tradingsymbol=symbol, exchange="NSE",
                    transaction_type=result.decision, quantity=qty,
                    product="MIS", order_type="MARKET",
                )
                logger.info("[LIVE] order %s: %s %s x%d", order_id,
                            result.decision, symbol, qty)
            except KiteClientError as exc:
                logger.error("Order failed for %s: %s", symbol, exc)
                self._record_trade(symbol, result, qty, stop_loss, "FAILED",
                                   paper, claude_used, order_id)
                return

        self._record_trade(symbol, result, qty, stop_loss, "OPEN",
                           paper, claude_used, order_id)

    def _record_trade(self, symbol: str, result: strategy.StrategyResult,
                      qty: int, stop_loss: float, status: str, paper: int,
                      claude_used: int, order_id: Optional[str]) -> None:
        reason = (f"score={result.confidence:.0f} "
                  f"indicators={result.indicators} claude={bool(claude_used)}")
        with database.get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO trades(symbol, exchange, segment, action, quantity, "
                "entry_price, stop_loss, status, paper_mode, confidence, reason, "
                "kite_order_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (symbol, "NSE", "EQ", result.decision, qty, result.last_price,
                 stop_loss, status, paper, result.confidence, reason, order_id),
            )
            conn.commit()

    def manage_open_positions(self) -> None:
        """Update trailing stops and close positions whose stop is hit."""
        with database.get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status = 'OPEN'"
            ).fetchall()

        for row in rows:
            symbol = row["symbol"]
            try:
                current_price = self._current_price(symbol)
            except KiteClientError as exc:
                logger.warning("No price for open %s: %s", symbol, exc)
                continue

            atr_guess = abs(row["entry_price"] - (row["stop_loss"] or 0)) / 2.0 or 1.0
            new_sl = trailing_stop_loss(
                entry_price=row["entry_price"], current_price=current_price,
                atr=atr_guess, action=row["action"],
                current_sl=row["stop_loss"] or row["entry_price"],
            )
            if new_sl != row["stop_loss"]:
                with database.get_connection(self.db_path) as conn:
                    conn.execute("UPDATE trades SET stop_loss = ? WHERE id = ?",
                                 (new_sl, row["id"]))
                    conn.commit()

            hit = ((row["action"] == "BUY" and current_price <= new_sl)
                   or (row["action"] == "SELL" and current_price >= new_sl))
            if hit:
                self._close_trade(row["id"], symbol, row["action"], row["quantity"],
                                  row["entry_price"], current_price,
                                  bool(row["paper_mode"]), "stop-loss hit")

    def _current_price(self, symbol: str) -> float:
        """Best-effort current price; uses LTP live, last candle close in paper."""
        if self._effective_paper():
            df = self.kite.historical_candles(symbol, interval="15minute", count=2)
            return float(df["close"].iloc[-1])
        return self.kite.ltp(symbol)

    def _close_trade(self, trade_id: int, symbol: str, action: str, qty: int,
                     entry: float, exit_price: float, paper: bool,
                     reason: str) -> None:
        pnl = (exit_price - entry) * qty if action == "BUY" else (entry - exit_price) * qty
        if not paper:
            close_side = "SELL" if action == "BUY" else "BUY"
            try:
                self.kite.place_order(
                    tradingsymbol=symbol, exchange="NSE",
                    transaction_type=close_side, quantity=qty,
                    product="MIS", order_type="MARKET",
                )
            except KiteClientError as exc:
                logger.error("Failed to close %s: %s", symbol, exc)
                return
        with database.get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE trades SET status='CLOSED', exit_price=?, pnl=?, "
                "reason=COALESCE(reason,'')||' | close: '||? WHERE id=?",
                (exit_price, pnl, reason, trade_id),
            )
            conn.commit()
        logger.info("Closed %s %s x%d pnl=%.2f (%s)", action, symbol, qty, pnl, reason)
        # Closing a trade may breach the daily loss limit.
        self.risk.check_daily_loss()

    def square_off_all(self) -> None:
        """Close every open position (hard 15:15 IST rule)."""
        with database.get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status = 'OPEN'"
            ).fetchall()
        for row in rows:
            try:
                price = self._current_price(row["symbol"])
            except KiteClientError:
                price = row["entry_price"]
            self._close_trade(row["id"], row["symbol"], row["action"],
                              row["quantity"], row["entry_price"], price,
                              bool(row["paper_mode"]), "square-off 15:15")
