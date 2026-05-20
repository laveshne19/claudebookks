import os
import tempfile

os.environ["PAPER_DATA_SOURCE"] = "synthetic"  # avoid network during tests

from app.auth import verify_password
from app.config import get_settings
from app.db import Database
from app.runtime import _Runtime


def fresh_runtime():
    get_settings.cache_clear()  # pick up the synthetic feed env
    rt = _Runtime()
    rt.init(Database(os.path.join(tempfile.mkdtemp(), "rt.db")))
    return rt


def test_default_login_seeded():
    rt = fresh_runtime()
    assert rt.cfg.dashboard_user == "admin"
    assert verify_password("changeme", rt.cfg.dashboard_password_hash)


def test_safe_config_redacts_secrets():
    rt = fresh_runtime()
    rt.apply_settings({"anthropic_api_key": "SK-ANT-SECRET-AAA", "dhan_access_token": "DHAN-TOKEN-BBB"})
    cfg = rt.safe_config()
    assert "SK-ANT-SECRET-AAA" not in str(cfg)
    assert "DHAN-TOKEN-BBB" not in str(cfg)
    assert cfg["has_anthropic_key"] is True
    assert cfg["has_dhan_token"] is True


def test_blank_secret_does_not_wipe_saved():
    rt = fresh_runtime()
    rt.apply_settings({"anthropic_api_key": "sk-keepme"})
    rt.apply_settings({"anthropic_api_key": ""})  # blank -> ignored
    assert rt.cfg.anthropic_api_key == "sk-keepme"


def test_password_change_persists():
    rt = fresh_runtime()
    rt.apply_settings({"dashboard_password": "newpass123"})
    assert verify_password("newpass123", rt.cfg.dashboard_password_hash)
    assert not verify_password("changeme", rt.cfg.dashboard_password_hash)


def test_risk_update_applies_in_place():
    rt = fresh_runtime()
    rt.engine  # ensure built
    rt.apply_settings({"max_trade_value": 9999, "max_open_positions": 7})
    assert rt.engine.risk.max_trade_value == 9999
    assert rt.engine.risk.max_open_positions == 7


def test_live_without_creds_falls_back_to_paper():
    rt = fresh_runtime()
    rt.apply_settings({"mode": "live"})  # no dhan creds/security map
    assert rt.cfg.effective_mode == "paper"
    assert rt.engine.broker.name == "paper"


def test_strategy_switch_to_claude():
    rt = fresh_runtime()
    rt.apply_settings({"strategy": "claude_advisor"})
    assert rt.engine.strategy.name == "claude_advisor"
