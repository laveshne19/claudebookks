"""Dhan broker adapter (live mode).

Implements the DhanHQ v2 REST API: https://dhanhq.co/docs/v2/

IMPORTANT: This places REAL orders with REAL money when used. It is only
selected when TRADING_MODE=live and valid DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN
are present. Verify the security_id mapping for your symbols before going live
— Dhan identifies instruments by numeric security_id, not ticker.
"""
from __future__ import annotations

import httpx

from ..models import Order, OrderStatus, Position, Side

BASE_URL = "https://api.dhan.co/v2"


class DhanBroker:
    name = "dhan"

    def __init__(self, client_id: str, access_token: str, security_map: dict[str, str] | None = None):
        self._client_id = client_id
        self._token = access_token
        # symbol -> Dhan security_id (NSE equity). Must be populated for live use.
        self._security_map = security_map or {}
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={
                "access-token": access_token,
                "client-id": client_id,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=10.0,
        )

    # --- helpers ---------------------------------------------------------
    def _security_id(self, symbol: str) -> str:
        sid = self._security_map.get(symbol.upper())
        if not sid:
            raise ValueError(
                f"No Dhan security_id mapped for {symbol}. Populate SECURITY_MAP."
            )
        return sid

    # --- BrokerAdapter ---------------------------------------------------
    def cash(self) -> float:
        try:
            r = self._client.get("/fundlimit")
            r.raise_for_status()
            data = r.json()
            return float(data.get("availabelBalance", data.get("availableBalance", 0)))
        except Exception:
            return 0.0

    def positions(self) -> list[Position]:
        try:
            r = self._client.get("/positions")
            r.raise_for_status()
            out: list[Position] = []
            for p in r.json() or []:
                qty = int(p.get("netQty", 0))
                if qty == 0:
                    continue
                out.append(
                    Position(
                        symbol=p.get("tradingSymbol", ""),
                        qty=qty,
                        avg_price=float(p.get("buyAvg") or p.get("costPrice") or 0),
                        last_price=float(p.get("ltp") or 0),
                    )
                )
            return out
        except Exception:
            return []

    def place_order(self, symbol: str, side: Side, qty: int, price: float, reason: str = "") -> Order:
        order = Order(symbol=symbol, side=side, qty=qty, price=price, reason=reason)
        try:
            payload = {
                "dhanClientId": self._client_id,
                "transactionType": side.value,
                "exchangeSegment": "NSE_EQ",
                "productType": "INTRADAY",
                "orderType": "MARKET",
                "validity": "DAY",
                "securityId": self._security_id(symbol),
                "quantity": qty,
                "price": 0,
            }
            r = self._client.post("/orders", json=payload)
            r.raise_for_status()
            data = r.json()
            order.order_id = str(data.get("orderId", ""))
            status = str(data.get("orderStatus", "")).upper()
            order.status = OrderStatus.FILLED if status in {"TRADED", "FILLED", "TRANSIT", "PENDING"} else OrderStatus.PENDING
            return order
        except Exception as exc:  # noqa: BLE001 - surface broker failures in the log
            order.status = OrderStatus.REJECTED
            order.reason = f"{reason} | dhan error: {exc}".strip(" |")
            return order

    def mark_prices(self, prices: dict[str, float]) -> None:
        # Live positions already carry broker-reported LTP; nothing to do.
        return
