"""Claude-powered commentary.

Claude does NOT place trades. It reads the current state (positions, P&L, recent
trades, market data) and produces plain-English analysis for the dashboard:
a daily summary, risk commentary, and per-trade rationale on request.

If ANTHROPIC_API_KEY is not set, every method degrades gracefully to a short
notice instead of raising.
"""
from __future__ import annotations

import json

SYSTEM_PROMPT = (
    "You are a trading-desk analyst assistant embedded in an automated trading "
    "dashboard for the Indian (NSE) market. You explain what the bot is doing and "
    "flag risks in clear, concise language for a non-expert owner. "
    "You are NOT a SEBI-registered investment adviser. Never promise profit. "
    "Always note uncertainty. Keep responses under 180 words unless asked otherwise."
)


class ClaudeAnalyst:
    def __init__(self, api_key: str, model: str):
        self._model = model
        self._client = None
        if api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=api_key)
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def _ask(self, prompt: str, max_tokens: int = 600) -> str:
        if not self._client:
            return "AI commentary unavailable — set ANTHROPIC_API_KEY to enable Claude analysis."
        try:
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            parts = [b.text for b in msg.content if getattr(b, "type", "") == "text"]
            return "\n".join(parts).strip() or "(empty response)"
        except Exception as exc:  # noqa: BLE001
            return f"AI commentary error: {exc}"

    def daily_summary(self, status: dict, trades: list[dict]) -> str:
        prompt = (
            "Summarise today's automated trading session for the owner. "
            "Cover: overall P&L, what positions are open and why, and any risk concerns. "
            "Here is the current state as JSON:\n\n"
            f"STATUS:\n{json.dumps(status, default=str)}\n\n"
            f"RECENT TRADES (newest first):\n{json.dumps(trades[:25], default=str)}"
        )
        return self._ask(prompt)

    def risk_commentary(self, status: dict) -> str:
        prompt = (
            "Given this trading bot state, point out the top 2-3 risks right now "
            "and whether the configured guardrails look adequate. Be specific.\n\n"
            f"{json.dumps(status, default=str)}"
        )
        return self._ask(prompt, max_tokens=400)

    def ask(self, question: str, status: dict, trades: list[dict]) -> str:
        prompt = (
            f"Owner question: {question}\n\n"
            "Answer using the live bot state below. If the question is outside what "
            "the data supports, say so.\n\n"
            f"STATUS:\n{json.dumps(status, default=str)}\n\n"
            f"RECENT TRADES:\n{json.dumps(trades[:25], default=str)}"
        )
        return self._ask(prompt, max_tokens=700)
