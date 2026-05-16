"""Round 2 backend tests — viewer role, permissions, location/attendance, AI, scheduler-triggered sync."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sales-force-hub-9.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@nalanda.com", "password": "Admin@123"}
SALES = {"email": "sales1@nalanda.com", "password": "Sales@123"}
ACCOUNTS = {"email": "accounts@nalanda.com", "password": "Accounts@123"}
MANAGER = {"email": "manager@nalanda.com", "password": "Manager@123"}
BOAT = {"email": "boat@nalanda.com", "password": "Boat@123"}


def login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text[:300]}"
    return r.json()["token"], r.json()["user"]


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- Viewer (Boat partner) ----------
class TestViewer:
    def test_boat_login(self):
        token, user = login(BOAT)
        assert user["email"] == BOAT["email"]
        assert user["role"] == "viewer"
        assert "effective_permissions" in user
        perms = user["effective_permissions"]
        assert "Boat" in (perms.get("brands") or []), f"Boat brand missing: {perms}"
        # Viewer should have no customer visibility
        assert perms.get("customer_visibility") == "none"
        # Should only have Dashboard module
        modules = perms.get("modules") or []
        assert "dashboard" in modules
        assert "customers" not in modules
        assert "admin" not in modules

    def test_boat_customers_empty(self):
        token, _ = login(BOAT)
        r = requests.get(f"{API}/customers", headers=H(token), timeout=15)
        assert r.status_code == 200
        assert r.json() == [], "Viewer should see no customers"

    def test_boat_viewer_dashboard(self):
        token, _ = login(BOAT)
        r = requests.get(f"{API}/dashboard/viewer", headers=H(token), timeout=20)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "scope" in d and "totals" in d and "daily" in d
        assert d["scope"]["brands"] == ["Boat"], f"expected brands=['Boat'], got {d['scope']['brands']}"
        # totals shape
        assert d["totals"]["grand_total"] >= 0
        # daily rows should NOT contain customer info
        for row in d["daily"]:
            assert "date" in row and "total" in row
            for k in row.keys():
                assert k not in ("customer_id", "customer_name", "name", "code")

    def test_boat_cannot_access_admin_dashboard(self):
        token, _ = login(BOAT)
        r = requests.get(f"{API}/dashboard/admin", headers=H(token), timeout=15)
        assert r.status_code == 403


# ---------- Auth /me includes effective_permissions ----------
class TestEffectivePermissions:
    @pytest.mark.parametrize("creds", [ADMIN, SALES, ACCOUNTS, MANAGER, BOAT])
    def test_me_has_effective_permissions(self, creds):
        token, _ = login(creds)
        r = requests.get(f"{API}/auth/me", headers=H(token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "effective_permissions" in d, f"missing effective_permissions for {creds['email']}"
        perms = d["effective_permissions"]
        for k in ("modules", "brands", "view_scope", "customer_visibility"):
            assert k in perms, f"missing perm key {k} for {creds['email']}"


# ---------- Permission management ----------
class TestPermissionsManagement:
    def test_permissions_options(self):
        token, _ = login(ADMIN)
        r = requests.get(f"{API}/permissions/options", headers=H(token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("modules", "brands", "view_scopes", "customer_visibility", "roles"):
            assert k in d and isinstance(d[k], list) and len(d[k]) > 0

    def test_permissions_options_sales_denied(self):
        token, _ = login(SALES)
        r = requests.get(f"{API}/permissions/options", headers=H(token), timeout=15)
        assert r.status_code == 403

    def test_admin_can_override_permissions(self):
        token, _ = login(ADMIN)
        # find sales1 user id
        users = requests.get(f"{API}/users", headers=H(token), timeout=15).json()
        sales_user = next(u for u in users if u["email"] == SALES["email"])
        uid = sales_user["id"]
        payload = {"can_export": True, "can_edit": True}
        r = requests.patch(f"{API}/users/{uid}/permissions", headers=H(token), json=payload, timeout=15)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("effective_permissions", {}).get("can_export") is True
        assert d.get("effective_permissions", {}).get("can_edit") is True


# ---------- Location & Attendance ----------
class TestLocationAttendance:
    def test_sales_ping_creates_attendance(self):
        token, user = login(SALES)
        body = {"lat": 19.0760, "lng": 72.8777, "accuracy": 12.5}
        r = requests.post(f"{API}/location/ping", headers=H(token), json=body, timeout=15)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("ok") is True

        # Today attendance for this user should exist
        r2 = requests.get(f"{API}/attendance", headers=H(token), timeout=15)
        assert r2.status_code == 200
        recs = r2.json()
        assert isinstance(recs, list) and len(recs) >= 1
        for rec in recs:
            assert rec["user_id"] == user["id"]

    def test_admin_attendance_today(self):
        # Make sure a ping exists
        stoken, _ = login(SALES)
        requests.post(f"{API}/location/ping", headers=H(stoken),
                      json={"lat": 19.07, "lng": 72.87}, timeout=15)
        atoken, _ = login(ADMIN)
        r = requests.get(f"{API}/attendance/today", headers=H(atoken), timeout=15)
        assert r.status_code == 200
        recs = r.json()
        assert isinstance(recs, list) and len(recs) >= 1
        assert any(rec.get("checked_in") for rec in recs)
        # Ensure expected fields present
        for rec in recs:
            for k in ("user_id", "name", "checked_in", "ping_count"):
                assert k in rec

    def test_admin_location_latest(self):
        atoken, _ = login(ADMIN)
        r = requests.get(f"{API}/location/latest", headers=H(atoken), timeout=15)
        assert r.status_code == 200
        recs = r.json()
        assert isinstance(recs, list)
        # at least one sales rep entry
        assert len(recs) >= 1
        for rec in recs:
            assert "id" in rec or "user_id" in rec or "name" in rec

    def test_attendance_sales_only_own(self):
        token, user = login(SALES)
        r = requests.get(f"{API}/attendance", headers=H(token), timeout=15)
        assert r.status_code == 200
        for rec in r.json():
            assert rec["user_id"] == user["id"]


# ---------- AI Route plan & Performance (LIVE) ----------
class TestAILive:
    def test_route_plan(self):
        token, _ = login(SALES)
        r = requests.get(f"{API}/ai/route-plan?max_stops=5", headers=H(token), timeout=45)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "plan" in d and "summary" in d
        assert isinstance(d["plan"], list)
        if d["plan"]:
            stop0 = d["plan"][0]
            for k in ("order", "customer_id", "reason", "objective", "suggested_time", "customer"):
                assert k in stop0, f"missing {k} in plan item"

    def test_performance(self):
        token, _ = login(SALES)
        r = requests.get(f"{API}/ai/performance", headers=H(token), timeout=45)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for k in ("summary", "rating", "strengths", "gaps", "next_actions",
                  "predicted_month_end_pct", "metrics"):
            assert k in d, f"missing {k} in AI performance response"
        assert d["rating"] in ("exceptional", "on_track", "behind", "critical")


# ---------- Scheduler / Sync ----------
class TestZohoSyncTriggers:
    def test_zoho_sync_runs_aggregate_refresh(self):
        token, _ = login(ADMIN)
        r = requests.post(f"{API}/sync/zoho", headers=H(token), timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("status") in ("completed", "failed")
        assert "message" in d


# ---------- Sales regression ----------
class TestSalesRegression:
    def test_sales_dashboard_still_works(self):
        token, _ = login(SALES)
        r = requests.get(f"{API}/dashboard/sales", headers=H(token), timeout=20)
        assert r.status_code == 200
        for k in ("kpis", "sales_trend", "aging", "priority_customers"):
            assert k in r.json()

    def test_admin_full_access(self):
        token, _ = login(ADMIN)
        for path in ("/dashboard/admin", "/dashboard/sales", "/dashboard/accounts", "/customers", "/users"):
            r = requests.get(f"{API}{path}", headers=H(token), timeout=20)
            assert r.status_code == 200, f"admin failed {path} -> {r.status_code}"


# ---------- PWA assets ----------
class TestPWAAssets:
    @pytest.mark.parametrize("path", ["/manifest.json", "/service-worker.js", "/icon-192.png", "/icon-512.png"])
    def test_asset_accessible(self, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=15)
        assert r.status_code == 200, f"{path} returned {r.status_code}"
        assert len(r.content) > 0
