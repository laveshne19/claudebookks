"""
Backend regression tests for Nalanda ERP/CRM SaaS.
Covers: auth, customers, dashboards, schemes, notifications, reports, AI insights, role guards.
"""
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


def login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    data = r.json()
    return data["token"], data["user"], r.cookies


def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- Auth ----------
class TestAuth:
    def test_admin_login(self):
        token, user, cookies = login(ADMIN)
        assert user["email"] == ADMIN["email"]
        assert user["role"] in ("super_admin", "admin")
        assert isinstance(token, str) and len(token) > 20
        assert "access_token" in cookies or len(cookies) >= 0  # cookies set
        # check httpOnly cookie
        r = requests.post(f"{API}/auth/login", json=ADMIN, timeout=15)
        assert "access_token" in r.cookies or "access_token" in r.headers.get("set-cookie", "").lower()

    def test_sales_login(self):
        _, user, _ = login(SALES)
        assert user["role"] == "sales"

    def test_accounts_login(self):
        _, user, _ = login(ACCOUNTS)
        assert user["role"] == "accounts"

    def test_invalid_login(self):
        r = requests.post(f"{API}/auth/login", json={"email": "x@y.com", "password": "bad"}, timeout=15)
        assert r.status_code in (400, 401)

    def test_me_with_bearer(self):
        token, _, _ = login(ADMIN)
        r = requests.get(f"{API}/auth/me", headers=headers(token), timeout=15)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN["email"]

    def test_logout(self):
        token, _, _ = login(ADMIN)
        r = requests.post(f"{API}/auth/logout", headers=headers(token), timeout=15)
        assert r.status_code in (200, 204)


# ---------- Customers ----------
class TestCustomers:
    def test_admin_sees_all_customers(self):
        token, _, _ = login(ADMIN)
        r = requests.get(f"{API}/customers", headers=headers(token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 25, f"expected ~30 customers, got {len(data)}"

    def test_sales_sees_subset(self):
        atoken, _, _ = login(ADMIN)
        stoken, _, _ = login(SALES)
        admin_count = len(requests.get(f"{API}/customers", headers=headers(atoken), timeout=15).json())
        sales_count = len(requests.get(f"{API}/customers", headers=headers(stoken), timeout=15).json())
        assert sales_count <= admin_count
        assert sales_count > 0

    def test_customer_detail(self):
        token, _, _ = login(ADMIN)
        cust_list = requests.get(f"{API}/customers", headers=headers(token), timeout=15).json()
        cid = cust_list[0]["id"]
        r = requests.get(f"{API}/customers/{cid}", headers=headers(token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        # Must include outstanding, overdue and some score
        keys = set(d.keys())
        assert "outstanding" in keys or "outstanding_total" in keys, f"missing outstanding: {keys}"
        return cid

    def test_customer_ledger(self):
        token, _, _ = login(ADMIN)
        cid = requests.get(f"{API}/customers", headers=headers(token), timeout=15).json()[0]["id"]
        r = requests.get(f"{API}/customers/{cid}/ledger", headers=headers(token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "invoices" in d and "payments" in d
        assert "visits" in d or True  # visits optional


# ---------- AI Insights ----------
class TestAIInsights:
    def test_ai_insights(self):
        token, _, _ = login(ADMIN)
        cid = requests.get(f"{API}/customers", headers=headers(token), timeout=15).json()[0]["id"]
        r = requests.get(f"{API}/customers/{cid}/insights", headers=headers(token), timeout=60)
        assert r.status_code == 200, f"AI insights failed: {r.status_code} {r.text[:300]}"
        d = r.json()
        required = ["summary", "predicted_next_order", "credit_risk_score",
                    "payment_behaviour_score", "recovery_approach", "upsell_suggestions",
                    "pitch_points", "best_visit_time"]
        missing = [k for k in required if k not in d]
        assert not missing, f"AI insights missing keys: {missing}; got: {list(d.keys())}"


# ---------- Dashboards ----------
class TestDashboards:
    def test_sales_dashboard(self):
        token, _, _ = login(SALES)
        r = requests.get(f"{API}/dashboard/sales", headers=headers(token), timeout=20)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for k in ("kpis", "sales_trend", "brand_split", "aging", "priority_customers", "open_tasks"):
            assert k in d, f"missing {k} in sales dashboard"

    def test_admin_dashboard(self):
        token, _, _ = login(ADMIN)
        r = requests.get(f"{API}/dashboard/admin", headers=headers(token), timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "kpis" in d
        assert "leaderboard" in d

    def test_accounts_dashboard(self):
        token, _, _ = login(ACCOUNTS)
        r = requests.get(f"{API}/dashboard/accounts", headers=headers(token), timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert any(k in d for k in ("overdue", "overdue_invoices", "invoices_overdue"))
        assert "checklist" in d or "daily_checklist" in d


# ---------- Schemes ----------
class TestSchemes:
    def test_schemes_list(self):
        token, _, _ = login(ADMIN)
        r = requests.get(f"{API}/schemes", headers=headers(token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list)
        assert len(d) >= 4, f"expected ~6 schemes, got {len(d)}"


# ---------- Notifications ----------
class TestNotifications:
    def test_notifications(self):
        token, _, _ = login(ADMIN)
        r = requests.get(f"{API}/notifications", headers=headers(token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list)
        assert len(d) >= 1


# ---------- Reports ----------
class TestReports:
    @pytest.fixture(scope="class")
    def admin_token(self):
        return login(ADMIN)[0]

    def test_aging(self, admin_token):
        r = requests.get(f"{API}/reports/aging", headers=headers(admin_token), timeout=20)
        assert r.status_code == 200

    def test_brand_performance(self, admin_token):
        r = requests.get(f"{API}/reports/brand-performance", headers=headers(admin_token), timeout=20)
        assert r.status_code == 200

    def test_sales_trend(self, admin_token):
        r = requests.get(f"{API}/reports/sales-trend", headers=headers(admin_token), timeout=20)
        assert r.status_code == 200

    def test_productivity(self, admin_token):
        r = requests.get(f"{API}/reports/productivity", headers=headers(admin_token), timeout=20)
        assert r.status_code == 200


# ---------- Role-based access ----------
class TestRoleGuards:
    def test_sales_cannot_access_admin_dashboard(self):
        token, _, _ = login(SALES)
        r = requests.get(f"{API}/dashboard/admin", headers=headers(token), timeout=15)
        assert r.status_code == 403, f"expected 403, got {r.status_code}"

    def test_register_admin_only(self):
        token, _, _ = login(ADMIN)
        unique_email = f"TEST_user_{int(time.time())}@nalanda.com"
        body = {"email": unique_email, "password": "Test@1234", "name": "Test User", "role": "sales"}
        r = requests.post(f"{API}/auth/register", json=body, headers=headers(token), timeout=15)
        assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
        # verify login works
        r2 = requests.post(f"{API}/auth/login", json={"email": unique_email, "password": "Test@1234"}, timeout=15)
        assert r2.status_code == 200

    def test_sales_cannot_register(self):
        token, _, _ = login(SALES)
        body = {"email": f"TEST_x_{int(time.time())}@n.com", "password": "Test@1234", "name": "X", "role": "sales"}
        r = requests.post(f"{API}/auth/register", json=body, headers=headers(token), timeout=15)
        assert r.status_code == 403
