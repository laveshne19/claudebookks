"""Interactive CLI to generate a daily Kite access token.

Kite access tokens expire every morning (~06:00 IST). Run::

    python -m app.kite_login

The script prints the login URL, waits for you to paste back the
``request_token`` from the redirect, exchanges it for an ``access_token``,
and persists it to both the ``.env`` file and the ``config`` DB table.

No browser automation is used (Selenium etc. is explicitly forbidden).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from app import database
from app.config import PROJECT_ROOT, load_config
from app.kite_client import KiteAuthError, KiteClient

logger = logging.getLogger(__name__)


def _persist_token(token: str) -> None:
    """Write the access token to the DB and update the .env file in place."""
    database.set_config("kite_access_token", token)
    database.set_state("token_generated_at", database_now())

    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        logger.warning(".env not found; token saved to DB only")
        return

    lines = env_path.read_text().splitlines()
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("KITE_ACCESS_TOKEN="):
            lines[i] = f"KITE_ACCESS_TOKEN={token}"
            updated = True
            break
    if not updated:
        lines.append(f"KITE_ACCESS_TOKEN={token}")
    env_path.write_text("\n".join(lines) + "\n")
    logger.info("Access token written to .env and DB")


def database_now() -> str:
    """Return the current UTC timestamp as an ISO string (for bot_state)."""
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main() -> int:
    """Run the interactive token-generation flow.

    Returns:
        int: Process exit code (0 on success).
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = load_config()
    if not cfg.kite_api_key or not cfg.kite_api_secret:
        logger.error("KITE_API_KEY and KITE_API_SECRET must be set in .env")
        return 2

    database.init_db(cfg.db_path)
    client = KiteClient(cfg.kite_api_key, cfg.kite_api_secret)

    print("\n1) Open this URL in your browser and log in to Kite:\n")
    print(f"   {client.login_url()}\n")
    print("2) After login you'll be redirected to a URL containing")
    print("   'request_token=XXedit'. Copy that request_token value.\n")
    try:
        request_token = input("Paste request_token here: ").strip()
    except (EOFError, KeyboardInterrupt):
        logger.error("Aborted by user")
        return 1
    if not request_token:
        logger.error("No request_token provided")
        return 2

    try:
        access_token = client.generate_session(request_token)
    except KiteAuthError as exc:
        logger.error("Failed to generate session: %s", exc)
        return 1

    _persist_token(access_token)

    # Verify the token works by fetching the profile.
    try:
        profile = client.profile()
        logger.info("Logged in as %s (%s)",
                    profile.get("user_name"), profile.get("user_id"))
    except KiteAuthError as exc:
        logger.error("Token saved but profile check failed: %s", exc)
        return 1
    print("\nToken generated and verified. You can now run: python -m app.main\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
