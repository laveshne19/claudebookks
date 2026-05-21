"""Thin, defensive wrapper around the Zerodha KiteConnect SDK.

This module is a pure broker API adapter. It performs NO paper/live decision
making — that responsibility belongs to :mod:`app.trader`, which checks the
paper-mode flag before ever calling :meth:`KiteClient.place_order`.

All external responses are validated before use (per the defensive-coding
requirement); malformed data raises :class:`KiteClientError`.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

try:  # The SDK is an optional import so tests can run without it installed.
    from kiteconnect import KiteConnect
    from kiteconnect.exceptions import KiteException, TokenException
except ImportError:  # pragma: no cover - exercised only in minimal envs
    KiteConnect = None  # type: ignore[assignment]
    KiteException = Exception  # type: ignore[assignment,misc]
    TokenException = Exception  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)


class KiteClientError(RuntimeError):
    """Raised when the broker API returns malformed or unexpected data."""


class KiteAuthError(KiteClientError):
    """Raised when the access token is missing, invalid, or expired."""


class KiteClient:
    """Wrapper exposing the subset of KiteConnect this bot needs.

    Args:
        api_key: Kite API key.
        api_secret: Kite API secret (used only during session generation).
        access_token: Daily access token; may be empty before login.

    Raises:
        KiteClientError: If the kiteconnect SDK is not installed.
    """

    def __init__(self, api_key: str, api_secret: str,
                 access_token: str = "") -> None:
        if KiteConnect is None:
            raise KiteClientError(
                "kiteconnect SDK not installed; run pip install -r requirements.txt"
            )
        self._api_key = api_key
        self._api_secret = api_secret
        self._kite = KiteConnect(api_key=api_key)
        self._instrument_cache: Dict[str, int] = {}
        if access_token:
            self._kite.set_access_token(access_token)

    # -- Authentication -----------------------------------------------------

    def login_url(self) -> str:
        """Return the Kite Connect login URL the user must visit."""
        return self._kite.login_url()

    def generate_session(self, request_token: str) -> str:
        """Exchange a request token for an access token.

        Args:
            request_token: The token returned in the redirect after login.

        Returns:
            str: The freshly minted access token.

        Raises:
            KiteAuthError: If the exchange fails.
        """
        try:
            data = self._kite.generate_session(
                request_token, api_secret=self._api_secret
            )
        except KiteException as exc:
            raise KiteAuthError(f"Session generation failed: {exc}") from exc
        token = data.get("access_token") if isinstance(data, dict) else None
        if not token:
            raise KiteAuthError("No access_token in session response")
        self._kite.set_access_token(token)
        return token

    def set_access_token(self, access_token: str) -> None:
        """Set the access token on the underlying client."""
        self._kite.set_access_token(access_token)

    def profile(self) -> Dict[str, Any]:
        """Fetch the user profile (verifies the token is valid).

        Returns:
            dict: The profile payload.

        Raises:
            KiteAuthError: If the token is invalid/expired.
            KiteClientError: On other API errors.
        """
        try:
            data = self._kite.profile()
        except TokenException as exc:
            raise KiteAuthError(f"Token invalid/expired: {exc}") from exc
        except KiteException as exc:
            raise KiteClientError(f"profile() failed: {exc}") from exc
        if not isinstance(data, dict):
            raise KiteClientError("Unexpected profile response shape")
        return data

    # -- Market data --------------------------------------------------------

    def _load_instruments(self, exchange: str = "NSE") -> None:
        """Populate the tradingsymbol -> instrument_token cache for an exchange."""
        try:
            instruments = self._kite.instruments(exchange)
        except KiteException as exc:
            raise KiteClientError(f"instruments({exchange}) failed: {exc}") from exc
        if not isinstance(instruments, list):
            raise KiteClientError("Unexpected instruments response shape")
        cache: Dict[str, int] = {}
        for row in instruments:
            sym = row.get("tradingsymbol")
            token = row.get("instrument_token")
            if sym and token is not None:
                cache[sym] = int(token)
        self._instrument_cache = cache
        logger.info("Loaded %d instruments for %s", len(cache), exchange)

    def instrument_token(self, tradingsymbol: str, exchange: str = "NSE") -> int:
        """Resolve a tradingsymbol to its numeric instrument token.

        Args:
            tradingsymbol: e.g. ``RELIANCE``.
            exchange: Exchange code; defaults to ``NSE``.

        Returns:
            int: The instrument token.

        Raises:
            KiteClientError: If the symbol cannot be resolved.
        """
        if not self._instrument_cache:
            self._load_instruments(exchange)
        token = self._instrument_cache.get(tradingsymbol)
        if token is None:
            raise KiteClientError(f"Unknown tradingsymbol: {tradingsymbol}")
        return token

    def historical_candles(self, tradingsymbol: str, interval: str = "15minute",
                           count: int = 100, exchange: str = "NSE") -> pd.DataFrame:
        """Fetch recent historical candles as a DataFrame.

        Args:
            tradingsymbol: e.g. ``RELIANCE``.
            interval: Kite interval string; defaults to ``15minute``.
            count: Number of most-recent candles to request.
            exchange: Exchange code.

        Returns:
            pandas.DataFrame: Columns ``date, open, high, low, close, volume``.

        Raises:
            KiteClientError: On API error or malformed data.
        """
        import datetime as _dt

        token = self.instrument_token(tradingsymbol, exchange)
        # 15-min candles: ~25 per day; request enough calendar days to cover count.
        days_back = max(5, int(count / 25) + 5)
        to_date = _dt.datetime.now()
        from_date = to_date - _dt.timedelta(days=days_back)
        try:
            raw = self._kite.historical_data(
                instrument_token=token, from_date=from_date,
                to_date=to_date, interval=interval,
            )
        except TokenException as exc:
            raise KiteAuthError(f"Token invalid/expired: {exc}") from exc
        except KiteException as exc:
            raise KiteClientError(f"historical_data failed: {exc}") from exc
        if not isinstance(raw, list) or not raw:
            raise KiteClientError(f"No candle data for {tradingsymbol}")
        df = pd.DataFrame(raw)
        required = {"date", "open", "high", "low", "close", "volume"}
        if not required.issubset(df.columns):
            raise KiteClientError(
                f"Candle data missing columns: {required - set(df.columns)}"
            )
        return df.tail(count).reset_index(drop=True)

    def ltp(self, tradingsymbol: str, exchange: str = "NSE") -> float:
        """Return the last traded price for a symbol.

        Raises:
            KiteClientError: On API error or missing price.
        """
        key = f"{exchange}:{tradingsymbol}"
        try:
            data = self._kite.ltp([key])
        except KiteException as exc:
            raise KiteClientError(f"ltp failed: {exc}") from exc
        try:
            return float(data[key]["last_price"])
        except (KeyError, TypeError, ValueError) as exc:
            raise KiteClientError(f"Malformed ltp response for {key}") from exc

    # -- Orders & positions -------------------------------------------------

    def place_order(self, *, tradingsymbol: str, exchange: str, transaction_type: str,
                    quantity: int, product: str = "MIS",
                    order_type: str = "MARKET", price: Optional[float] = None) -> str:
        """Place a LIVE order. CALLER MUST have verified live mode first.

        Args:
            tradingsymbol: e.g. ``RELIANCE``.
            exchange: e.g. ``NSE``.
            transaction_type: ``BUY`` or ``SELL``.
            quantity: Number of shares (> 0).
            product: Product code; defaults to ``MIS`` (intraday).
            order_type: ``MARKET`` or ``LIMIT``.
            price: Limit price (required for LIMIT orders).

        Returns:
            str: The broker order id.

        Raises:
            ValueError: If quantity is not positive.
            KiteClientError: On API error or missing order id.
        """
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        try:
            order_id = self._kite.place_order(
                variety=self._kite.VARIETY_REGULAR,
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                transaction_type=transaction_type,
                quantity=quantity,
                product=product,
                order_type=order_type,
                price=price,
            )
        except KiteException as exc:
            raise KiteClientError(f"place_order failed: {exc}") from exc
        if not order_id:
            raise KiteClientError("place_order returned no order id")
        return str(order_id)

    def positions(self) -> List[Dict[str, Any]]:
        """Return current net positions.

        Returns:
            list[dict]: The ``net`` positions list (possibly empty).

        Raises:
            KiteClientError: On API error or malformed data.
        """
        try:
            data = self._kite.positions()
        except KiteException as exc:
            raise KiteClientError(f"positions failed: {exc}") from exc
        if not isinstance(data, dict) or "net" not in data:
            raise KiteClientError("Unexpected positions response shape")
        return list(data["net"])
