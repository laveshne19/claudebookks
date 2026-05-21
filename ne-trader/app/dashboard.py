"""FastAPI dashboard for monitoring and limited manual control.

Pages: ``/`` (P&L, positions, recent trades, status), ``/logs``, ``/config``,
``/scans``. Actions: stop bot, square off all, toggle paper mode (confirm),
and ``/auth/refresh`` for the daily Kite token flow.

Security:
- HTTP Basic auth (credentials from ``.env``), constant-time compared.
- The app is bound to ``DASHBOARD_BIND`` (default 127.0.0.1) by the launcher;
  it must never be exposed on 0.0.0.0 publicly.
- The paper-mode toggle can only *enable* paper mode (the safe direction).
  Going live requires editing ``LIVE_MODE`` in ``.env`` and restarting.
"""

from __future__ import annotations

import logging
import secrets
from pathlib import Path
from typing import Callable, Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from app import database
from app.config import Config

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class DashboardControls:
    """Hooks the dashboard uses to act on the running bot.

    Each attribute is a callable injected by :mod:`app.main`. Defaults are
    no-ops so the dashboard can run standalone (e.g. in tests).
    """

    def __init__(self) -> None:
        self.stop_bot: Callable[[], None] = lambda: None
        self.square_off_all: Callable[[], None] = lambda: None
        self.force_paper_mode: Callable[[], None] = lambda: None
        self.refresh_token: Callable[[str], bool] = lambda _t: False
        self.login_url: Callable[[], str] = lambda: ""


def create_app(cfg: Config, controls: Optional[DashboardControls] = None,
               db_path: Optional[Path] = None) -> FastAPI:
    """Build and return the FastAPI dashboard application.

    Args:
        cfg: Loaded configuration (for auth credentials and display).
        controls: Optional control hooks into the running bot.
        db_path: Optional explicit DB path (defaults to ``cfg.db_path``).

    Returns:
        FastAPI: The configured application.
    """
    controls = controls or DashboardControls()
    path = db_path or cfg.db_path
    app = FastAPI(title="NE Kite Autotrader", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    security = HTTPBasic()

    def require_auth(creds: HTTPBasicCredentials = Depends(security)) -> str:
        user_ok = secrets.compare_digest(creds.username, cfg.dashboard_username)
        pass_ok = secrets.compare_digest(creds.password, cfg.dashboard_password)
        if not (user_ok and pass_ok) or not cfg.dashboard_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Basic"},
            )
        return creds.username

    def _query(sql: str, args: tuple = ()) -> list:
        with database.get_connection(path) as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def _scalar(sql: str, args: tuple = ()) -> float:
        with database.get_connection(path) as conn:
            row = conn.execute(sql, args).fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, _user: str = Depends(require_auth)) -> HTMLResponse:
        import datetime as dt
        today = dt.date.today().isoformat()
        pnl_today = _scalar(
            "SELECT COALESCE(SUM(pnl),0) FROM trades WHERE status='CLOSED' "
            "AND DATE(timestamp)=?", (today,))
        pnl_all = _scalar(
            "SELECT COALESCE(SUM(pnl),0) FROM trades WHERE status='CLOSED'")
        open_positions = _query(
            "SELECT * FROM trades WHERE status='OPEN' ORDER BY id DESC")
        recent = _query(
            "SELECT * FROM trades WHERE status='CLOSED' ORDER BY id DESC LIMIT 20")
        kill = database.get_state("kill_switch_triggered", "0", path) == "1"
        last_scan = database.get_state("last_scan_time", "never", path)
        return templates.TemplateResponse(request, "index.html", {
            "pnl_today": pnl_today, "pnl_all": pnl_all,
            "open_positions": open_positions, "recent": recent,
            "kill_switch": kill, "last_scan": last_scan,
            "paper_mode": cfg.paper_mode,
        })

    @app.get("/logs", response_class=HTMLResponse)
    def logs(request: Request, _user: str = Depends(require_auth)) -> HTMLResponse:
        log_file = cfg.log_dir / "trader.log"
        lines: list[str] = []
        if log_file.exists():
            lines = log_file.read_text(errors="replace").splitlines()[-100:]
        return templates.TemplateResponse(request, "logs.html", {"lines": lines})

    @app.get("/scans", response_class=HTMLResponse)
    def scans(request: Request, _user: str = Depends(require_auth)) -> HTMLResponse:
        rows = _query("SELECT * FROM scan_log ORDER BY id DESC LIMIT 100")
        return templates.TemplateResponse(request, "scans.html", {"scans": rows})

    @app.get("/config", response_class=HTMLResponse)
    def config_page(request: Request,
                    _user: str = Depends(require_auth)) -> HTMLResponse:
        return templates.TemplateResponse(request, "config.html", {
            "cfg": cfg,
            "db_overrides": _query("SELECT * FROM config ORDER BY key"),
        })

    @app.post("/config")
    def config_save(key: str = Form(...), value: str = Form(...),
                    _user: str = Depends(require_auth)) -> RedirectResponse:
        # Only a safe allowlist of keys is editable from the UI.
        allowed = {"min_confidence", "risk_per_trade_pct",
                   "daily_loss_limit_pct", "max_open_positions"}
        if key in allowed:
            database.set_config(key, value, path)
        return RedirectResponse("/config", status_code=303)

    @app.post("/action/stop")
    def action_stop(_user: str = Depends(require_auth)) -> RedirectResponse:
        controls.stop_bot()
        return RedirectResponse("/", status_code=303)

    @app.post("/action/squareoff")
    def action_squareoff(_user: str = Depends(require_auth)) -> RedirectResponse:
        controls.square_off_all()
        return RedirectResponse("/", status_code=303)

    @app.post("/action/paper")
    def action_paper(confirm: str = Form(""),
                     _user: str = Depends(require_auth)) -> RedirectResponse:
        # Can only force paper mode ON (the safe direction).
        if confirm == "yes":
            controls.force_paper_mode()
        return RedirectResponse("/", status_code=303)

    @app.get("/auth/refresh", response_class=HTMLResponse)
    def auth_refresh(request: Request,
                     _user: str = Depends(require_auth)) -> HTMLResponse:
        return templates.TemplateResponse(request, "auth.html", {
            "login_url": controls.login_url()})

    @app.post("/auth/refresh")
    def auth_refresh_post(request_token: str = Form(...),
                          _user: str = Depends(require_auth)) -> RedirectResponse:
        controls.refresh_token(request_token.strip())
        return RedirectResponse("/", status_code=303)

    return app
