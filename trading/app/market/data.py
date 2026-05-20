"""Market data providers.

Two implementations:
  * DhanData      - real LTP via the Dhan quote API (used in live mode).
  * SyntheticData - a seeded random walk so the whole system (engine, dashboard,
                    paper trading) runs end-to-end with no broker, no network,
                    and no API keys. Clearly fake — for development/demo only.

Both expose ohlc-style history via a rolling in-memory price buffer so
indicators (SMA/RSI) have something to chew on immediately.
"""
from __future__ import annotations

import random
from collections import defaultdict, deque

import httpx

from ..models import Quote


class PriceHistory:
    """Rolling close-price buffer per symbol."""

    def __init__(self, maxlen: int = 300):
        self._buf: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=maxlen))

    def push(self, symbol: str, price: float) -> None:
        self._buf[symbol].append(price)

    def closes(self, symbol: str) -> list[float]:
        return list(self._buf[symbol])


class SyntheticData:
    """Deterministic-ish random walk. Good enough to exercise strategies."""

    name = "synthetic"

    _BASE = {
        "RELIANCE": 2900.0,
        "TCS": 3850.0,
        "INFY": 1550.0,
        "HDFCBANK": 1680.0,
        "SBIN": 820.0,
    }

    def __init__(self, symbols: list[str], seed: int = 42):
        self._rng = random.Random(seed)
        self._price = {s: self._BASE.get(s, 1000.0) for s in symbols}
        self.history = PriceHistory()
        # Warm up history so indicators are usable from the first loop.
        for _ in range(60):
            for s in symbols:
                self._step(s)

    def _step(self, symbol: str) -> float:
        drift = 0.0002
        vol = 0.004
        p = self._price[symbol]
        ret = self._rng.gauss(drift, vol)
        p = max(1.0, p * (1 + ret))
        self._price[symbol] = p
        self.history.push(symbol, p)
        return p

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        out: dict[str, Quote] = {}
        for s in symbols:
            price = round(self._step(s), 2)
            out[s] = Quote(symbol=s, ltp=price)
        return out


class DhanData:
    """Live LTP via Dhan market quote API."""

    name = "dhan"

    def __init__(self, client_id: str, access_token: str, security_map: dict[str, str]):
        self._security_map = security_map
        self._rev = {v: k for k, v in security_map.items()}
        self.history = PriceHistory()
        self._client = httpx.Client(
            base_url="https://api.dhan.co/v2",
            headers={
                "access-token": access_token,
                "client-id": client_id,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=10.0,
        )

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        ids = [int(self._security_map[s]) for s in symbols if s in self._security_map]
        if not ids:
            return {}
        out: dict[str, Quote] = {}
        try:
            r = self._client.post("/marketfeed/ltp", json={"NSE_EQ": ids})
            r.raise_for_status()
            data = r.json().get("data", {}).get("NSE_EQ", {})
            for sid, payload in data.items():
                sym = self._rev.get(str(sid))
                if not sym:
                    continue
                ltp = float(payload.get("last_price", 0))
                if ltp > 0:
                    self.history.push(sym, ltp)
                    out[sym] = Quote(symbol=sym, ltp=round(ltp, 2))
        except Exception:
            return {}
        return out


class YFinanceData:
    """Free real NSE prices via Yahoo Finance (yfinance). No API key.

    Used as the default paper-mode feed so paper trading runs on real (delayed)
    market prices. Requires internet access to Yahoo Finance from the host.
    Quotes are ~15 min delayed — fine for paper testing, not for live HFT.
    """

    name = "yfinance (NSE, delayed)"

    def __init__(self, symbols: list[str]):
        import yfinance as yf  # imported lazily so the dep is optional

        self._yf = yf
        self._symbols = symbols
        self._ymap = {s: f"{s}.NS" for s in symbols}  # NSE suffix
        self._rev = {v: k for k, v in self._ymap.items()}
        self.history = PriceHistory()
        self._warmup()

    def _warmup(self) -> None:
        """Seed indicator history with recent intraday closes. Raises if no
        data comes back, so build_provider can fall back to synthetic."""
        tickers = list(self._ymap.values())
        df = self._yf.download(
            tickers=tickers, period="5d", interval="15m",
            group_by="ticker", auto_adjust=True, progress=False, threads=True,
        )
        got_any = False
        for ysym in tickers:
            try:
                closes = df[ysym]["Close"].dropna().tolist() if len(tickers) > 1 else df["Close"].dropna().tolist()
            except (KeyError, TypeError):
                closes = []
            sym = self._rev[ysym]
            for c in closes[-120:]:
                self.history.push(sym, float(c))
                got_any = True
        if not got_any:
            raise RuntimeError("yfinance returned no data for the configured symbols")

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        out: dict[str, Quote] = {}
        tickers = [self._ymap[s] for s in symbols if s in self._ymap]
        try:
            df = self._yf.download(
                tickers=tickers, period="1d", interval="1m",
                group_by="ticker", auto_adjust=True, progress=False, threads=True,
            )
        except Exception:
            return {}
        for ysym in tickers:
            try:
                series = df[ysym]["Close"].dropna() if len(tickers) > 1 else df["Close"].dropna()
                if series.empty:
                    continue
                ltp = round(float(series.iloc[-1]), 2)
            except (KeyError, TypeError, IndexError):
                continue
            if ltp > 0:
                sym = self._rev[ysym]
                self.history.push(sym, ltp)
                out[sym] = Quote(symbol=sym, ltp=ltp)
        return out


def build_provider(settings) -> "SyntheticData | DhanData | YFinanceData":
    """Pick a data provider based on configuration.

    * live + dhan + security_map -> real Dhan feed
    * paper + PAPER_DATA_SOURCE=live -> real yfinance feed (fallback: synthetic)
    * otherwise -> synthetic random walk
    """
    if settings.effective_mode == "live" and settings.broker == "dhan":
        security_map = getattr(settings, "security_map", None)
        if not security_map:
            import os, json

            raw = os.getenv("SECURITY_MAP", "")
            try:
                security_map = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                security_map = {}
        if security_map:
            return DhanData(settings.dhan_client_id, settings.dhan_access_token, security_map)

    if settings.paper_data_source == "live":
        try:
            return YFinanceData(settings.symbols)
        except Exception:
            if not settings.allow_synthetic_feed:
                raise
            # fall through to synthetic

    return SyntheticData(settings.symbols)
