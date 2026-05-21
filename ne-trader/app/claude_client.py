"""Claude AI overlay: an optional second-opinion layer over rule signals.

After the rules produce a qualifying signal, the trader asks Claude whether to
proceed. Claude may veto with ``HOLD``; any other/ambiguous answer or API error
falls through to the rules-only decision (the overlay must never block trades
on API failure, per spec).

Uses prompt caching on the static system instructions to reduce cost.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None  # type: ignore[assignment]

if TYPE_CHECKING:  # avoid runtime import cost / cycles
    import pandas as pd

    from app.strategy import StrategyResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a conservative risk-overlay for an intraday Indian-equities (NSE, "
    "MIS) trading bot. A rule-based engine has already produced a signal using "
    "EMA, RSI, MACD, Supertrend and momentum. Your ONLY job is to veto clearly "
    "bad trades. Respond with a single JSON object: "
    '{\"decision\": \"BUY\"|\"SELL\"|\"HOLD\", \"reason\": \"<short>\"}. '
    "Return HOLD only when the candle action or context strongly contradicts the "
    "rule signal. When in doubt, agree with the rules. No prose outside the JSON."
)


class ClaudeOverlay:
    """Wrapper around the Anthropic Messages API for trade second-opinions.

    Args:
        api_key: Anthropic API key (must be non-empty).
        model: Model id to use.

    Raises:
        RuntimeError: If the anthropic SDK is unavailable or key is empty.
    """

    def __init__(self, api_key: str, model: str) -> None:
        if anthropic is None:
            raise RuntimeError("anthropic SDK not installed")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is empty")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def second_opinion(self, *, symbol: str, result: "StrategyResult",
                       candles: "pd.DataFrame", open_positions: int) -> str:
        """Return Claude's verdict (``BUY``/``SELL``/``HOLD``).

        On any error, returns the rules' original decision so trading is never
        blocked by the overlay.

        Args:
            symbol: Trading symbol under consideration.
            result: The rule-engine strategy result.
            candles: Recent candle DataFrame (last 20 rows are sent).
            open_positions: Current count of open positions.

        Returns:
            str: ``BUY``, ``SELL`` or ``HOLD``.
        """
        recent = candles.tail(20)[["open", "high", "low", "close", "volume"]]
        payload = {
            "symbol": symbol,
            "rule_decision": result.decision,
            "buy_score": result.buy_score,
            "sell_score": result.sell_score,
            "indicators": result.indicators,
            "last_price": result.last_price,
            "atr": result.atr,
            "open_positions": open_positions,
            "recent_candles": recent.round(2).to_dict(orient="records"),
        }
        try:
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=256,
                system=[{
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": json.dumps(payload)}],
            )
            text = "".join(
                block.text for block in msg.content
                if getattr(block, "type", None) == "text"
            ).strip()
            verdict = self._parse(text)
            logger.info("Claude verdict for %s: %s (rules=%s)",
                        symbol, verdict, result.decision)
            return verdict
        except Exception as exc:  # noqa: BLE001 - never block trades on overlay
            logger.warning("Claude API error (%s); falling back to rules", exc)
            return result.decision

    @staticmethod
    def _parse(text: str) -> str:
        """Extract the decision field from Claude's JSON reply, defensively."""
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            data = json.loads(text[start:end])
            decision = str(data.get("decision", "")).upper()
            if decision in {"BUY", "SELL", "HOLD"}:
                return decision
        except (ValueError, json.JSONDecodeError):
            pass
        # Fall back to keyword scan.
        upper = text.upper()
        if "HOLD" in upper:
            return "HOLD"
        if "SELL" in upper:
            return "SELL"
        return "BUY"
