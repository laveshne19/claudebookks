"""
Round 3 backend regression: Today's Beat + Scheme Management
Tests new endpoints introduced for:
  - GET  /api/beat/today            (admin + sales scope)
  - POST /api/beat/visit            (mark visit + update last_visit_date)
  - GET  /api/schemes/brands        (zoho or default fallback)
  - POST /api/schemes               (admin create)
  - POST /api/schemes/upload        (CSV multipart upload)
  - POST /api/schemes/{id}/recompute
  - GET  /api/schemes/{id}/leaderboard
  - DELETE /api/schemes/{id}
"""
import os
import io
import time
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or "https://sales-force-hub-9.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@nalanda.com", "password": "Admin@123"}
NAVNEET = {"email": "navneet@nalanda.com", "password": "Sales@123"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text[:300]}"
    return r.json()["token"]


def _h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def sales_token():
    return _login(NAVNEET)


# ---------- Beat Today ----------
class TestBeatToday:
    def test_admin_beat_today(self, admin_token):
        r = requests.get(f"{API}/beat/today", headers=_h(admin_token), timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "summary" in d and "stops" in d
        s = d["summary"]
        for k in ("weekday", "count", "platinum", "diamond", "gold", "silver",
                  "total_outstanding", "total_overdue"):
            assert k in s, f"missing key {k} in summary: {list(s.keys())}"
        assert isinstance(d["stops"], list)
        # Validate any stop record shape (lazy: only when populated)
        if d["stops"]:
            stop = d["stops"][0]
            for k in ("id", "name", "tier"):
                assert k in stop, f"stop missing {k}"

    def test_sales_beat_today_only_assigned(self, admin_token, sales_token):
        r = requests.get(f"{API}/beat/today", headers=_h(sales_token), timeout=30)
        assert r.status_code == 200
        sales_data = r.json()
        # Sales role should ONLY see their assigned stops
        admin_data = requests.get(f"{API}/beat/today", headers=_h(admin_token), timeout=30).json()
        # Sanity: sales count should be <= admin count
        assert sales_data["summary"]["count"] <= admin_data["summary"]["count"]
        # All stops belong to navneet's assignment — backend filters by assigned_to.
        # We can't easily get navneet's user_id without /auth/me, fetch it.
        me = requests.get(f"{API}/auth/me", headers=_h(sales_token), timeout=15).json()
        sales_user_id = me["id"]
        for stop in sales_data["stops"]:
            assigned = stop.get("assigned_to")
            if assigned is not None:
                assert assigned == sales_user_id, f"sales sees unassigned customer: {stop}"

    def test_beat_visit_create_and_persist(self, sales_token):
        # Get a beat candidate
        r = requests.get(f"{API}/beat/today", headers=_h(sales_token), timeout=30)
        stops = r.json().get("stops", [])
        if not stops:
            # Fallback to any customer the sales sees
            cust_list = requests.get(f"{API}/customers", headers=_h(sales_token), timeout=20).json()
            assert cust_list, "no customers visible to sales user"
            cid = cust_list[0]["id"]
        else:
            cid = stops[0]["id"]

        body = {"customer_id": cid, "duration_minutes": 15, "notes": "TEST_beat_visit", "outcome": "followup"}
        r = requests.post(f"{API}/beat/visit", json=body, headers=_h(sales_token), timeout=20)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["customer_id"] == cid
        assert d["user_id"]
        assert d["notes"] == "TEST_beat_visit"
        assert "_id" not in d, "MongoDB _id leaked in response"

        # Persistence: customer.last_visit_date updated
        c = requests.get(f"{API}/customers/{cid}", headers=_h(sales_token), timeout=15).json()
        assert c.get("last_visit_date"), "last_visit_date not persisted"

    def test_beat_visit_validation(self, sales_token):
        r = requests.post(f"{API}/beat/visit", json={}, headers=_h(sales_token), timeout=15)
        assert r.status_code == 400


# ---------- Schemes ----------
class TestSchemes:
    def test_brands_endpoint(self, admin_token):
        r = requests.get(f"{API}/schemes/brands", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "source" in d and "brands" in d
        assert isinstance(d["brands"], list) and len(d["brands"]) > 0
        assert d["source"] in ("default", "zoho")

    def test_create_scheme_admin(self, admin_token):
        unique = uuid.uuid4().hex[:8]
        body = {
            "name": f"TEST_Boat_Q3_{unique}",
            "brand": "Boat",
            "start_date": "2025-10-01",
            "end_date": "2025-12-31",
            "target_amount": 500000,
            "reward": "5% rebate",
            "description": "Automated test scheme",
            "active": True,
        }
        r = requests.post(f"{API}/schemes", json=body, headers=_h(admin_token), timeout=20)
        assert r.status_code in (200, 201), r.text[:300]
        s = r.json()
        assert s["name"] == body["name"]
        assert s["brand"] == "Boat"
        assert "id" in s
        assert "_id" not in s, "MongoDB _id leaked"
        # GET to verify persistence
        listing = requests.get(f"{API}/schemes", headers=_h(admin_token), timeout=15).json()
        ids = [x["id"] for x in listing]
        assert s["id"] in ids
        # Cleanup
        requests.delete(f"{API}/schemes/{s['id']}", headers=_h(admin_token), timeout=15)

    def test_csv_upload(self, admin_token):
        unique = uuid.uuid4().hex[:6]
        csv = (
            "name,brand,start_date,end_date,target_amount,reward,description\n"
            f"TEST_Sch_A_{unique},Boat,2025-10-01,2025-12-31,300000,5% rebate,CSV upload A\n"
            f"TEST_Sch_B_{unique},JBL,2025-10-01,2025-12-31,200000,2% rebate,CSV upload B\n"
        )
        files = {"file": (f"schemes_{unique}.csv", io.BytesIO(csv.encode()), "text/csv")}
        r = requests.post(
            f"{API}/schemes/upload",
            files=files,
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for k in ("created", "updated", "skipped", "errors"):
            assert k in d, f"upload result missing key {k}: {d}"
        assert d["created"] >= 2 or (d["created"] + d["updated"]) >= 2
        # Cleanup created schemes
        listing = requests.get(f"{API}/schemes", headers=_h(admin_token), timeout=15).json()
        for sc in listing:
            if sc.get("name", "").startswith(f"TEST_Sch_") and unique in sc["name"]:
                requests.delete(f"{API}/schemes/{sc['id']}", headers=_h(admin_token), timeout=15)

    def test_recompute_and_leaderboard(self, admin_token):
        # Create a scheme to exercise the endpoint deterministically
        unique = uuid.uuid4().hex[:6]
        body = {
            "name": f"TEST_Recompute_{unique}",
            "brand": "Boat",
            "start_date": "2024-01-01",
            "end_date": "2026-12-31",
            "target_amount": 100000,
            "reward": "test",
            "active": True,
        }
        s = requests.post(f"{API}/schemes", json=body, headers=_h(admin_token), timeout=20).json()
        sid = s["id"]
        try:
            r = requests.post(f"{API}/schemes/{sid}/recompute", headers=_h(admin_token), timeout=30)
            assert r.status_code == 200, r.text[:300]
            d = r.json()
            assert "scheme" in d and "leaderboard" in d
            assert "total" in d
            assert d["scheme"]["id"] == sid
            assert isinstance(d["leaderboard"], list)
            # leaderboard entries should have resolved customer names if any
            if d["leaderboard"]:
                top = d["leaderboard"][0]
                assert "customer_name" in top or "name" in top, f"leaderboard entry missing name: {top}"

            r2 = requests.get(f"{API}/schemes/{sid}/leaderboard", headers=_h(admin_token), timeout=30)
            assert r2.status_code == 200
            d2 = r2.json()
            assert "leaderboard" in d2 and "scheme" in d2
        finally:
            requests.delete(f"{API}/schemes/{sid}", headers=_h(admin_token), timeout=15)

    def test_schemes_list_no_object_id(self, admin_token):
        r = requests.get(f"{API}/schemes", headers=_h(admin_token), timeout=15)
        assert r.status_code == 200
        for s in r.json():
            assert "_id" not in s, f"scheme leaks _id: {s}"

    def test_recompute_requires_admin(self, sales_token, admin_token):
        # Pick an existing scheme
        listing = requests.get(f"{API}/schemes", headers=_h(admin_token), timeout=15).json()
        if not listing:
            pytest.skip("no schemes available")
        sid = listing[0]["id"]
        r = requests.post(f"{API}/schemes/{sid}/recompute", headers=_h(sales_token), timeout=15)
        assert r.status_code == 403
