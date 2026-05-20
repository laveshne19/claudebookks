"""FastAPI application: REST API + WebSocket + static dashboard.

Run with:  uvicorn app.main:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from apscheduler.schedulers.background import BackgroundScheduler

from .ai.claude import ClaudeAnalyst
from .brokers.dhan import DhanBroker
from .brokers.paper import PaperBroker
from .config import get_settings
from .db import Database
from .engine.risk import RiskManager
from .engine.trader import TradingEngine
from .market.data import build_provider
from .strategy.registry import available as strategies_available, get_strategy

STATIC_DIR = Path(__file__).parent / "static"

settings = get_settings()
db = Database(settings.db_path)

# --- broker selection ----------------------------------------------------
import json as _json
import os as _os


def _security_map() -> dict[str, str]:
    raw = _os.getenv("SECURITY_MAP", "")
    try:
        return _json.loads(raw) if raw else {}
    except _json.JSONDecodeError:
        return {}


if settings.effective_mode == "live" and settings.broker == "dhan":
    broker = DhanBroker(settings.dhan_client_id, settings.dhan_access_token, _security_map())
else:
    broker = PaperBroker(settings.starting_cash)

data_provider = build_provider(settings)
strategy = get_strategy(settings.strategy)
risk = RiskManager(
    max_trade_value=settings.max_trade_value,
    max_open_positions=settings.max_open_positions,
    daily_loss_limit=settings.daily_loss_limit,
    stop_loss_pct=settings.stop_loss_pct,
    take_profit_pct=settings.take_profit_pct,
)
engine = TradingEngine(
    broker=broker,
    data_provider=data_provider,
    strategy=strategy,
    risk=risk,
    db=db,
    settings=settings,
)
analyst = ClaudeAnalyst(settings.anthropic_api_key, settings.anthropic_model)

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


def _scheduled_loop():
    try:
        engine.run_once()
    except Exception as exc:  # noqa: BLE001 - never let a loop error kill the scheduler
        engine.last_loop_note = f"loop error: {exc}"


app = FastAPI(title="Indian Market Auto-Trader", version="0.1.0")


@app.on_event("startup")
def _startup():
    if settings.autostart:
        engine.start()
    scheduler.add_job(
        _scheduled_loop,
        "interval",
        seconds=settings.loop_interval_seconds,
        id="trade_loop",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()


@app.on_event("shutdown")
def _shutdown():
    with contextlib.suppress(Exception):
        scheduler.shutdown(wait=False)
    db.close()


# --- API models ----------------------------------------------------------
class AskBody(BaseModel):
    question: str


# --- REST ----------------------------------------------------------------
@app.get("/api/status")
def api_status():
    return engine.status()


@app.get("/api/trades")
def api_trades(limit: int = 200):
    return db.recent_trades(limit)


@app.get("/api/equity")
def api_equity(limit: int = 500):
    return db.equity_curve(limit)


@app.get("/api/config")
def api_config():
    return {
        "mode": settings.mode,
        "effective_mode": settings.effective_mode,
        "broker": settings.broker,
        "strategies": strategies_available(),
        "ai_enabled": analyst.available,
        "loop_interval_seconds": settings.loop_interval_seconds,
    }


@app.post("/api/start")
def api_start():
    engine.start()
    return engine.status()


@app.post("/api/stop")
def api_stop():
    engine.stop()
    return engine.status()


@app.post("/api/step")
def api_step():
    """Run one decision loop immediately (ignores running/market-hours gate)."""
    result = engine.run_once(force=True)
    return {"result": result, "status": engine.status()}


@app.post("/api/panic")
def api_panic():
    closed = engine.panic_flatten()
    return {"closed": closed, "status": engine.status()}


@app.post("/api/market-hours/{flag}")
def api_market_hours(flag: bool):
    engine.respect_market_hours = flag
    return engine.status()


@app.get("/api/ai/summary")
def api_ai_summary():
    return {"summary": analyst.daily_summary(engine.status(), db.recent_trades(50))}


@app.get("/api/ai/risk")
def api_ai_risk():
    return {"commentary": analyst.risk_commentary(engine.status())}


@app.post("/api/ai/ask")
def api_ai_ask(body: AskBody):
    return {"answer": analyst.ask(body.question, engine.status(), db.recent_trades(50))}


# --- WebSocket: push status every few seconds ----------------------------
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(
                {"status": engine.status(), "trades": db.recent_trades(30)}
            )
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
    except Exception:
        with contextlib.suppress(Exception):
            await websocket.close()


# --- Dashboard ------------------------------------------------------------
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "dashboard.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
