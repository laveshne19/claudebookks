"""Claude-driven strategy.

Claude is given recent prices + indicators + whether we hold the symbol, and
returns a structured BUY / SELL / HOLD decision. The decision is NOT executed
blindly — it still flows through the RiskManager (position sizing, per-trade
cap, max positions, daily loss limit, stop-loss/take-profit, kill switch),
exactly like the deterministic strategies.

To control cost/latency it only re-queries Claude for a symbol every
`decision_interval` seconds; in between it returns HOLD.

WARNING: letting an LLM drive live orders is inherently risky (latency, cost,
hallucination, knowledge cutoff). Use in paper mode first and keep tight
guardrails. This is not investment advice.
"""
from __future__ import annotations

import json
import re
import time

from ..models import Side, Signal
from .base import Strategy
from .indicators import rsi, sma

SYSTEM = (
    "You are a disciplined intraday trading decision engine for NSE equities. "
    "Given recent prices and indicators for ONE stock, decide the next action. "
    "Respond with ONLY a JSON object: {\"action\": \"BUY\"|\"SELL\"|\"HOLD\", "
    "\"reason\": \"<=15 words\"}. No prose, no markdown. Be conservative: prefer "
    "HOLD unless there is a clear trend/momentum signal. Never risk-manage here "
    "(position size and stops are handled elsewhere)."
)


class ClaudeStrategy(Strategy):
    name = "claude_advisor"
    warmup = 22

    def __init__(self, api_key: str, model: str, decision_interval: int = 300, client=None):
        self.model = model
        self.decision_interval = max(30, int(decision_interval))
        self._last_call: dict[str, float] = {}
        self._client = client
        if client is None and api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=api_key)
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def _cooldown_active(self, symbol: str) -> bool:
        last = self._last_call.get(symbol, 0.0)
        return (time.monotonic() - last) < self.decision_interval

    def _build_prompt(self, symbol: str, closes: list[float], holding: bool) -> str:
        recent = [round(c, 2) for c in closes[-30:]]
        return json.dumps(
            {
                "symbol": symbol,
                "currently_holding_long": holding,
                "last_price": recent[-1] if recent else None,
                "sma_9": round(sma(closes, 9), 2) if sma(closes, 9) else None,
                "sma_21": round(sma(closes, 21), 2) if sma(closes, 21) else None,
                "rsi_14": round(rsi(closes, 14), 1) if rsi(closes, 14) else None,
                "recent_closes": recent,
            }
        )

    @staticmethod
    def _parse(text: str) -> tuple[str, str]:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return "HOLD", "unparseable response"
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return "HOLD", "invalid json"
        action = str(obj.get("action", "HOLD")).upper()
        if action not in {"BUY", "SELL", "HOLD"}:
            action = "HOLD"
        return action, str(obj.get("reason", ""))[:120]

    def evaluate(self, symbol: str, closes: list[float], holding: bool) -> Signal:
        if len(closes) < self.warmup:
            return Signal(symbol, None, reason="warming up")
        if not self._client:
            return Signal(symbol, None, reason="Claude key not set")
        if self._cooldown_active(symbol):
            return Signal(symbol, None, reason="claude cooldown")

        self._last_call[symbol] = time.monotonic()
        try:
            msg = self._client.messages.create(
                model=self.model,
                max_tokens=120,
                system=SYSTEM,
                messages=[{"role": "user", "content": self._build_prompt(symbol, closes, holding)}],
            )
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        except Exception as exc:  # noqa: BLE001
            return Signal(symbol, None, reason=f"claude error: {exc}")

        action, reason = self._parse(text)
        tag = f"Claude: {reason}"
        if action == "BUY" and not holding:
            return Signal(symbol, Side.BUY, reason=tag, strength=0.5)
        if action == "SELL" and holding:
            return Signal(symbol, Side.SELL, reason=tag)
        return Signal(symbol, None, reason=tag or "Claude: hold")
