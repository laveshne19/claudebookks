"""FastAPI application: auth + REST + WebSocket + static dashboard.

Run with:  uvicorn app.main:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

from . import auth
from .config import get_settings
from .db import Database
from .runtime import runtime
from .strategy.registry import available as strategies_available

STATIC_DIR = Path(__file__).parent / "static"

settings = get_settings()
db = Database(settings.db_path)
runtime.init(db)

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

# Paths reachable without a session.
PUBLIC_PREFIXES = ("/static", "/login", "/api/login", "/favicon")


def _scheduled_loop():
    try:
        runtime.engine.run_once()
    except Exception as exc:  # noqa: BLE001
        runtime.engine.last_loop_note = f"loop error: {exc}"


app = FastAPI(title="Indian Market Auto-Trader", version="0.2.0")


@app.middleware("http")
async def auth_gate(request: Request, call_next):
    path = request.url.path
    if path == "/" or path.startswith("/api") or path == "/settings":
        if not any(path.startswith(p) for p in PUBLIC_PREFIXES):
            token = request.cookies.get(auth.COOKIE_NAME, "")
            if not auth.verify_token(token, runtime.secret_key):
                if path.startswith("/api"):
                    return JSONResponse({"detail": "auth required"}, status_code=401)
                return RedirectResponse("/login", status_code=302)
    return await call_next(request)


@app.on_event("startup")
def _startup():
    if settings.autostart:
        runtime.engine.start()
    scheduler.add_job(
        _scheduled_loop,
        "interval",
        seconds=runtime.cfg.loop_interval_seconds,
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


class LoginBody(BaseModel):
    username: str
    password: str


class SettingsBody(BaseModel):
    updates: dict


# --- auth ----------------------------------------------------------------
@app.post("/api/login")
def api_login(body: LoginBody, response: Response):
    c = runtime.cfg
    if body.username != c.dashboard_user or not auth.verify_password(
        body.password, c.dashboard_password_hash
    ):
        return JSONResponse({"detail": "invalid credentials"}, status_code=401)
    token = auth.issue_token(body.username, runtime.secret_key)
    response.set_cookie(
        auth.COOKIE_NAME, token, httponly=True, samesite="lax", max_age=auth.SESSION_TTL
    )
    return {"ok": True}


@app.post("/api/logout")
def api_logout(response: Response):
    response.delete_cookie(auth.COOKIE_NAME)
    return {"ok": True}


# --- settings ------------------------------------------------------------
@app.get("/api/settings")
def api_get_settings():
    return runtime.safe_config()


@app.post("/api/settings")
def api_set_settings(body: SettingsBody):
    return runtime.apply_settings(body.updates)


# --- engine REST ---------------------------------------------------------
@app.get("/api/status")
def api_status():
    return runtime.engine.status()


@app.get("/api/trades")
def api_trades(limit: int = 200):
    return db.recent_trades(limit)


@app.get("/api/equity")
def api_equity(limit: int = 500):
    return db.equity_curve(limit)


@app.get("/api/config")
def api_config():
    return {
        **runtime.safe_config(),
        "strategies": strategies_available(),
        "ai_enabled": getattr(runtime.engine, "analyst", None) and runtime.engine.analyst.available,
    }


@app.post("/api/start")
def api_start():
    runtime.engine.start()
    return runtime.engine.status()


@app.post("/api/stop")
def api_stop():
    runtime.engine.stop()
    return runtime.engine.status()


@app.post("/api/step")
def api_step():
    result = runtime.engine.run_once(force=True)
    return {"result": result, "status": runtime.engine.status()}


@app.post("/api/panic")
def api_panic():
    closed = runtime.engine.panic_flatten()
    return {"closed": closed, "status": runtime.engine.status()}


@app.post("/api/market-hours/{flag}")
def api_market_hours(flag: bool):
    runtime.engine.respect_market_hours = flag
    return runtime.engine.status()


@app.get("/api/ai/summary")
def api_ai_summary():
    return {"summary": runtime.engine.analyst.daily_summary(runtime.engine.status(), db.recent_trades(50))}


@app.get("/api/ai/risk")
def api_ai_risk():
    return {"commentary": runtime.engine.analyst.risk_commentary(runtime.engine.status())}


@app.post("/api/ai/ask")
def api_ai_ask(body: AskBody):
    return {"answer": runtime.engine.analyst.ask(body.question, runtime.engine.status(), db.recent_trades(50))}


# --- WebSocket -----------------------------------------------------------
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    token = websocket.cookies.get(auth.COOKIE_NAME, "")
    if not auth.verify_token(token, runtime.secret_key):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(
                {"status": runtime.engine.status(), "trades": db.recent_trades(30)}
            )
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
    except Exception:
        with contextlib.suppress(Exception):
            await websocket.close()


# --- pages ---------------------------------------------------------------
@app.get("/login")
def login_page():
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "dashboard.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
