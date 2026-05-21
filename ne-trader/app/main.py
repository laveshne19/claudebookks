"""Application entry point: scheduler + dashboard, tied together.

Starts an in-process APScheduler that runs the scan loop every
``SCAN_INTERVAL_SECONDS`` and performs a hard square-off at 15:15 IST, then
serves the FastAPI dashboard with uvicorn. Handles SIGTERM/SIGINT for graceful
shutdown. No ``sleep()`` is used for timing (APScheduler handles all of it).

Run with::

    python -m app.main
"""

from __future__ import annotations

import logging
import logging.handlers
import signal
import sys
from types import FrameType
from typing import Optional

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app import database
from app.config import Config, load_config
from app.dashboard import DashboardControls, create_app
from app.kite_client import KiteAuthError, KiteClient, KiteClientError
from app.market import IST
from app.trader import Trader

logger = logging.getLogger(__name__)


def _setup_logging(cfg: Config) -> None:
    """Configure root logging with a rotating file handler + console."""
    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    log_file = cfg.log_dir / "trader.log"
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console)


def _build_claude(cfg: Config) -> Optional[object]:
    """Construct the Claude overlay if a key is configured, else None."""
    if not cfg.claude_enabled:
        logger.info("No Anthropic key; running rules-only (no Claude overlay)")
        return None
    try:
        from app.claude_client import ClaudeOverlay
        logger.info("Claude overlay enabled (model=%s)", cfg.anthropic_model)
        return ClaudeOverlay(cfg.anthropic_api_key, cfg.anthropic_model)
    except RuntimeError as exc:
        logger.warning("Claude overlay unavailable: %s", exc)
        return None


def main() -> int:
    """Boot the trader and dashboard. Returns a process exit code."""
    cfg = load_config()
    _setup_logging(cfg)
    database.init_db(cfg.db_path)

    kite = KiteClient(cfg.kite_api_key, cfg.kite_api_secret, cfg.kite_access_token)
    claude = _build_claude(cfg)
    trader = Trader(cfg, kite, claude=claude, db_path=cfg.db_path)

    scheduler = BackgroundScheduler(timezone=IST)

    def scan_job() -> None:
        try:
            trader.scan_once()
        except KiteAuthError:
            logger.error("Token invalid/expired during scan — refresh via "
                         "/auth/refresh or `python -m app.kite_login`")
        except KiteClientError as exc:
            logger.error("Broker error during scan: %s", exc)
        except Exception:  # noqa: BLE001 - scheduler must keep running
            logger.exception("Unexpected error in scan job")

    def squareoff_job() -> None:
        logger.info("Scheduled 15:15 IST square-off")
        try:
            trader.square_off_all()
        except Exception:  # noqa: BLE001
            logger.exception("Error during scheduled square-off")

    scheduler.add_job(scan_job, IntervalTrigger(seconds=cfg.scan_interval_seconds),
                      id="scan", max_instances=1, coalesce=True)
    scheduler.add_job(squareoff_job,
                      CronTrigger(hour=15, minute=15, timezone=IST),
                      id="squareoff")

    # Dashboard control hooks.
    controls = DashboardControls()
    controls.stop_bot = lambda: (scheduler.pause(),
                                 logger.warning("Bot paused via dashboard"))
    controls.square_off_all = trader.square_off_all
    controls.force_paper_mode = lambda: (
        database.set_state("force_paper", "1", cfg.db_path),
        logger.warning("Force-paper mode enabled via dashboard"))
    controls.login_url = kite.login_url

    def refresh(request_token: str) -> bool:
        try:
            token = kite.generate_session(request_token)
            database.set_config("kite_access_token", token, cfg.db_path)
            database.set_state("token_valid", "1", cfg.db_path)
            logger.info("Access token refreshed via dashboard")
            return True
        except KiteAuthError as exc:
            logger.error("Token refresh failed: %s", exc)
            return False
    controls.refresh_token = refresh

    app = create_app(cfg, controls, db_path=cfg.db_path)

    scheduler.start()
    logger.info("Scheduler started (scan every %ds). Dashboard on %s:%d",
                cfg.scan_interval_seconds, cfg.dashboard_bind, cfg.dashboard_port)

    def shutdown(signum: int, _frame: Optional[FrameType]) -> None:
        logger.info("Signal %s received; shutting down scheduler", signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    uvicorn.run(app, host=cfg.dashboard_bind, port=cfg.dashboard_port,
                log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
