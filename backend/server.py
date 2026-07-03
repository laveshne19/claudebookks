"""Nalanda Enterprises — ERP/CRM Backend (FastAPI + MongoDB)."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Query, UploadFile, File
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr

from auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, extract_token, get_current_user, require_roles,
)
from permissions import (
    default_permissions, user_permissions, can_access_module,
    filter_invoices_by_brands, filter_customers_by_brands, ALL_MODULES, ALL_BRANDS,
)
from models import (
    LoginRequest, RegisterRequest, UserOut,
    CustomerCreate, Customer,
    InvoiceCreate, Invoice,
    PaymentCreate, Payment,
    SchemeCreate, Scheme,
    TargetCreate, Target,
    NotificationCreate, Notification,
    TaskCreate, Task,
    VisitCreate, Visit,
    LocationPing, PermissionsPatch,
    new_id, now_iso,
)
from ai_service import get_or_generate_insights
from ai_planner import generate_route_plan, generate_performance_analysis
from seed_data import seed_database
from scheduler import start_scheduler, stop_scheduler, refresh_customer_aggregates
from zoho_sync import sync_zoho, detect_region_and_org, _credentials_present as zoho_creds_present
from excel_importer import import_all as import_historical
from mapping_importer import apply_mapping
from beat_planner import build_today_beat
from scheme_service import (
    upload_schemes_from_file, sync_zoho_brands,
    recompute_scheme_progress, recompute_all_schemes,
)
from data_upload_service import (
    upload_customers as svc_upload_customers,
    upload_beat_plans as svc_upload_beats,
    upload_salesperson_mapping as svc_upload_sp_mapping,
    get_template_csv,
)
from address_backfill import backfill_addresses as svc_backfill_addresses

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Mongo
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="Nalanda Enterprises ERP API")

# CORS — preview frontend on same domain, but allow_credentials needs explicit origins
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


# ========== STARTUP ==========
@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.customers.create_index("id", unique=True)
    await db.invoices.create_index("id", unique=True)
    await db.payments.create_index("id", unique=True)
    await db.schemes.create_index("id", unique=True)
    await db.targets.create_index("id", unique=True)
    await db.notifications.create_index("id", unique=True)
    await db.tasks.create_index("id", unique=True)
    await db.visits.create_index("id", unique=True)
    await db.ai_insights.create_index("customer_id", unique=True)
    await db.location_pings.create_index("user_id")
    await db.location_pings.create_index("timestamp")
    await db.attendance.create_index([("user_id", 1), ("date", 1)], unique=True)
    await db.credit_notes.create_index("id")
    await db.config.create_index("key", unique=True)

    # seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@nalanda.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": new_id(),
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "Super Admin",
            "role": "super_admin",
            "phone": "+91 98200 00000",
            "territory": "HQ",
            "active": True,
            "created_at": now_iso(),
        })
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})

    # seed sample data
    try:
        await seed_database(db)
    except Exception as e:
        logger.exception("Seed failed: %s", e)

    # start hourly aggregate scheduler
    try:
        start_scheduler(db)
    except Exception as e:
        logger.exception("Scheduler failed to start: %s", e)


@app.on_event("shutdown")
async def on_shutdown():
    stop_scheduler()
    client.close()


def _set_auth_cookies(response: Response, access: str, refresh: str):
    response.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=60*60*12, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="none", max_age=60*60*24*7, path="/")


def _strip_user(user: dict) -> dict:
    user = dict(user)
    user.pop("password_hash", None)
    user.pop("_id", None)
    # always attach effective permissions
    user["effective_permissions"] = user_permissions(user)
    return user


# ========== AUTH ==========
@api.post("/auth/login")
async def login(body: LoginRequest, response: Response):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated")

    access = create_access_token(user["id"], user["email"], user["role"])
    refresh = create_refresh_token(user["id"])
    _set_auth_cookies(response, access, refresh)
    return {"user": _strip_user(user), "token": access}


@api.post("/auth/register")
async def register(body: RegisterRequest, response: Response, current=Depends(require_roles("super_admin", "admin"))):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = {
        "id": new_id(),
        "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name,
        "role": body.role,
        "phone": body.phone,
        "territory": body.territory,
        "active": True,
        "created_at": now_iso(),
    }
    await db.users.insert_one(user)
    return _strip_user(user)


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    user["effective_permissions"] = user_permissions(user)
    return user


@api.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access = create_access_token(user["id"], user["email"], user["role"])
        response.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=60*60*12, path="/")
        return {"token": access}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# ========== USERS (ADMIN) ==========
@api.get("/users")
async def list_users(user=Depends(get_current_user)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(500)
    return users


@api.patch("/users/{user_id}")
async def update_user(user_id: str, payload: dict, current=Depends(require_roles("super_admin", "admin"))):
    allowed = {k: v for k, v in payload.items() if k in {"name", "role", "phone", "territory", "active"}}
    if "password" in payload and payload["password"]:
        allowed["password_hash"] = hash_password(payload["password"])
    await db.users.update_one({"id": user_id}, {"$set": allowed})
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    user["effective_permissions"] = user_permissions(user)
    return user


@api.patch("/users/{user_id}/permissions")
async def update_permissions(user_id: str, payload: PermissionsPatch, current=Depends(require_roles("super_admin", "admin"))):
    """Admin sets per-user permission overrides."""
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    existing = target.get("permissions") or {}
    update_data = payload.model_dump(exclude_unset=True)
    merged = {**existing, **update_data}
    await db.users.update_one({"id": user_id}, {"$set": {"permissions": merged}})
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    user["effective_permissions"] = user_permissions(user)
    return user


@api.get("/permissions/options")
async def permission_options(current=Depends(require_roles("super_admin", "admin"))):
    return {
        "modules": ALL_MODULES,
        "brands": ALL_BRANDS,
        "view_scopes": ["full", "aggregate_only", "totals_only"],
        "customer_visibility": ["assigned", "all", "none"],
        "roles": ["super_admin", "admin", "manager", "sales", "accounts", "viewer"],
    }


@api.delete("/users/{user_id}")
async def delete_user(user_id: str, current=Depends(require_roles("super_admin"))):
    await db.users.delete_one({"id": user_id})
    return {"ok": True}


# ========== CUSTOMERS ==========
@api.get("/customers")
async def list_customers(
    user=Depends(get_current_user),
    search: Optional[str] = None,
    area: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = 500,
):
    perms = user_permissions(user)
    # Customer visibility gate
    if perms["customer_visibility"] == "none":
        return []
    q = {}
    if perms["customer_visibility"] == "assigned":
        q["assigned_to"] = user["id"]
    if assigned_to:
        q["assigned_to"] = assigned_to
    if area:
        q["area"] = area
    if search:
        q["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"code": {"$regex": search, "$options": "i"}},
            {"area": {"$regex": search, "$options": "i"}},
        ]
    customers = await db.customers.find(q, {"_id": 0}).sort("name", 1).to_list(limit)
    customers = filter_customers_by_brands(customers, perms.get("brands") or [])
    return customers


@api.post("/customers")
async def create_customer(body: CustomerCreate, current=Depends(require_roles("super_admin", "admin", "manager"))):
    c = Customer(**body.model_dump()).model_dump()
    await db.customers.insert_one(c)
    return c


@api.get("/customers/{customer_id}")
async def get_customer(customer_id: str, user=Depends(get_current_user)):
    c = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return c


@api.patch("/customers/{customer_id}")
async def update_customer(customer_id: str, payload: dict, current=Depends(require_roles("super_admin", "admin", "manager", "sales"))):
    allowed_keys = {"name", "area", "city", "state", "contact_person", "phone", "email", "gstin", "credit_limit", "brand_preferences", "assigned_to", "lat", "lng"}
    upd = {k: v for k, v in payload.items() if k in allowed_keys}
    await db.customers.update_one({"id": customer_id}, {"$set": upd})
    return await db.customers.find_one({"id": customer_id}, {"_id": 0})


@api.get("/customers/{customer_id}/insights")
async def customer_insights(customer_id: str, force: bool = False, user=Depends(get_current_user)):
    insights = await get_or_generate_insights(db, customer_id, force=force)
    return insights


@api.get("/customers/{customer_id}/ledger")
async def customer_ledger(customer_id: str, user=Depends(get_current_user)):
    invoices = await db.invoices.find({"customer_id": customer_id}, {"_id": 0}).sort("date", -1).to_list(500)
    payments = await db.payments.find({"customer_id": customer_id}, {"_id": 0}).sort("date", -1).to_list(500)
    visits = await db.visits.find({"customer_id": customer_id}, {"_id": 0}).sort("date", -1).to_list(100)
    return {"invoices": invoices, "payments": payments, "visits": visits}


# ========== INVOICES ==========
@api.get("/invoices")
async def list_invoices(
    user=Depends(get_current_user),
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 500,
):
    q = {}
    if customer_id:
        q["customer_id"] = customer_id
    if status:
        q["status"] = status
    if user["role"] == "sales":
        cust_ids = [c["id"] for c in await db.customers.find({"assigned_to": user["id"]}, {"_id": 0, "id": 1}).to_list(1000)]
        q["customer_id"] = {"$in": cust_ids}
    invoices = await db.invoices.find(q, {"_id": 0}).sort("date", -1).to_list(limit)
    return invoices


@api.post("/invoices")
async def create_invoice(body: InvoiceCreate, current=Depends(require_roles("super_admin", "admin", "manager", "accounts"))):
    inv = Invoice(**body.model_dump()).model_dump()
    if not inv.get("invoice_no"):
        inv["invoice_no"] = f"INV-{datetime.now().year}-{int(datetime.now().timestamp())}"
    await db.invoices.insert_one(inv)
    return inv


# ========== PAYMENTS ==========
@api.get("/payments")
async def list_payments(user=Depends(get_current_user), customer_id: Optional[str] = None, limit: int = 500):
    q = {}
    if customer_id:
        q["customer_id"] = customer_id
    payments = await db.payments.find(q, {"_id": 0}).sort("date", -1).to_list(limit)
    return payments


@api.post("/payments")
async def create_payment(body: PaymentCreate, current=Depends(require_roles("super_admin", "admin", "accounts"))):
    p = Payment(**body.model_dump()).model_dump()
    await db.payments.insert_one(p)
    return p


# ========== SCHEMES ==========
@api.get("/schemes")
async def list_schemes(user=Depends(get_current_user), active: Optional[bool] = None):
    q = {}
    if active is not None:
        q["active"] = active
    return await db.schemes.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.post("/schemes")
async def create_scheme(body: SchemeCreate, current=Depends(require_roles("super_admin", "admin"))):
    s = Scheme(**body.model_dump()).model_dump()
    await db.schemes.insert_one(s)
    s.pop("_id", None)
    return s


@api.patch("/schemes/{scheme_id}")
async def update_scheme(scheme_id: str, payload: dict, current=Depends(require_roles("super_admin", "admin"))):
    await db.schemes.update_one({"id": scheme_id}, {"$set": payload})
    return await db.schemes.find_one({"id": scheme_id}, {"_id": 0})


@api.delete("/schemes/{scheme_id}")
async def delete_scheme(scheme_id: str, current=Depends(require_roles("super_admin", "admin"))):
    res = await db.schemes.delete_one({"id": scheme_id})
    return {"deleted": res.deleted_count}


@api.post("/schemes/upload")
async def upload_schemes(file: UploadFile = File(...), current=Depends(require_roles("super_admin", "admin"))):
    """Bulk upload schemes via Excel/CSV. Required columns: name, brand, start_date, end_date.
    Optional: type, description, target_amount, reward, active."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty file")
    res = await upload_schemes_from_file(db, content, file.filename or "")
    return res


@api.post("/schemes/sync-zoho-brands")
async def sync_zoho_brands_endpoint(current=Depends(require_roles("super_admin", "admin"))):
    """Pull item brand list from Zoho Books for the scheme creation dropdown."""
    return await sync_zoho_brands(db)


@api.get("/schemes/brands")
async def get_brand_list(user=Depends(get_current_user)):
    doc = await db.brands.find_one({"id": "zoho-brands"}, {"_id": 0})
    if not doc:
        # Fallback to constant brand list known to the system
        from permissions import ALL_BRANDS
        return {"source": "default", "brands": sorted(ALL_BRANDS)}
    return {"source": doc.get("source", "zoho"), "brands": doc.get("brands", []),
            "synced_at": doc.get("synced_at")}


@api.post("/schemes/{scheme_id}/recompute")
async def recompute_scheme(scheme_id: str, current=Depends(require_roles("super_admin", "admin", "manager"))):
    return await recompute_scheme_progress(db, scheme_id)


@api.post("/schemes/recompute-all")
async def recompute_all(current=Depends(require_roles("super_admin", "admin", "manager"))):
    return await recompute_all_schemes(db)


@api.get("/schemes/{scheme_id}/leaderboard")
async def scheme_leaderboard(scheme_id: str, user=Depends(get_current_user)):
    return await recompute_scheme_progress(db, scheme_id)


# ========== TARGETS ==========
@api.get("/targets")
async def list_targets(user=Depends(get_current_user), user_id: Optional[str] = None, period: Optional[str] = None):
    q = {}
    if user_id:
        q["user_id"] = user_id
    if period:
        q["period"] = period
    if user["role"] == "sales":
        q["user_id"] = user["id"]
    return await db.targets.find(q, {"_id": 0}).to_list(500)


@api.post("/targets")
async def create_target(body: TargetCreate, current=Depends(require_roles("super_admin", "admin", "manager"))):
    t = Target(**body.model_dump()).model_dump()
    await db.targets.insert_one(t)
    return t


# ========== TASKS ==========
@api.get("/tasks")
async def list_tasks(user=Depends(get_current_user), assigned_to: Optional[str] = None):
    q = {}
    if user["role"] == "sales":
        q["assigned_to"] = user["id"]
    elif assigned_to:
        q["assigned_to"] = assigned_to
    return await db.tasks.find(q, {"_id": 0}).sort("due_date", 1).to_list(500)


@api.post("/tasks")
async def create_task(body: TaskCreate, user=Depends(get_current_user)):
    t = Task(**body.model_dump()).model_dump()
    await db.tasks.insert_one(t)
    return t


@api.patch("/tasks/{task_id}")
async def update_task(task_id: str, payload: dict, user=Depends(get_current_user)):
    await db.tasks.update_one({"id": task_id}, {"$set": payload})
    return await db.tasks.find_one({"id": task_id}, {"_id": 0})


# ========== VISITS ==========
@api.get("/visits")
async def list_visits(user=Depends(get_current_user), customer_id: Optional[str] = None, user_id: Optional[str] = None):
    q = {}
    if customer_id:
        q["customer_id"] = customer_id
    if user_id:
        q["user_id"] = user_id
    if user["role"] == "sales":
        q["user_id"] = user["id"]
    return await db.visits.find(q, {"_id": 0}).sort("date", -1).to_list(500)


@api.post("/visits")
async def create_visit(body: VisitCreate, user=Depends(get_current_user)):
    v = Visit(**body.model_dump()).model_dump()
    await db.visits.insert_one(v)
    return v


# ========== NOTIFICATIONS ==========
@api.get("/notifications")
async def list_notifications(user=Depends(get_current_user), limit: int = 50):
    q = {"$or": [{"user_id": None}, {"user_id": user["id"]}]}
    return await db.notifications.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)


@api.post("/notifications")
async def create_notification(body: NotificationCreate, current=Depends(require_roles("super_admin", "admin", "manager"))):
    n = Notification(**body.model_dump()).model_dump()
    await db.notifications.insert_one(n)
    return n


@api.patch("/notifications/{nid}/read")
async def mark_read(nid: str, user=Depends(get_current_user)):
    await db.notifications.update_one({"id": nid}, {"$set": {"read": True}})
    return {"ok": True}


# ========== DASHBOARD ==========
@api.get("/dashboard/sales")
async def dashboard_sales(user=Depends(get_current_user)):
    """Salesperson dashboard data."""
    user_id = user["id"]
    if user["role"] in {"super_admin", "admin", "manager"}:
        # show aggregate
        target_query = {}
        cust_query = {}
    else:
        target_query = {"user_id": user_id}
        cust_query = {"assigned_to": user_id}

    period = datetime.now(timezone.utc).strftime("%Y-%m")
    targets = await db.targets.find({**target_query, "period": period}, {"_id": 0}).to_list(50)
    total_target = sum(t["target_amount"] for t in targets) or 0
    total_achieved = sum(t["achieved_amount"] for t in targets) or 0
    total_collect_target = sum(t.get("target_collection", 0) for t in targets) or 0
    total_collected = sum(t.get("collected_amount", 0) for t in targets) or 0

    customers = await db.customers.find(cust_query, {"_id": 0}).to_list(2000)
    total_outstanding = sum(c.get("outstanding", 0) for c in customers)
    total_overdue = sum(c.get("overdue", 0) for c in customers)
    cust_ids = [c["id"] for c in customers]

    inv_query = {"customer_id": {"$in": cust_ids}} if cust_ids else {}
    invoices = await db.invoices.find(inv_query, {"_id": 0}).to_list(5000)

    # MTD sales (current month)
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mtd_sales = sum(i["amount"] for i in invoices if i.get("date") and i["date"] >= month_start.isoformat())
    if mtd_sales == 0 and invoices:
        ninety = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        mtd_sales = sum(i["amount"] for i in invoices if i.get("date") and i["date"] >= ninety)

    # brand split — MTD, fallback to last-90, fallback to all-time
    brand_split = {}
    for inv in invoices:
        if inv.get("date") and inv["date"] >= month_start.isoformat():
            b = inv.get("brand", "Other")
            brand_split[b] = brand_split.get(b, 0) + inv["amount"]
    if not brand_split:
        ninety = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        for inv in invoices:
            if inv.get("date") and inv["date"] >= ninety:
                b = inv.get("brand", "Other")
                brand_split[b] = brand_split.get(b, 0) + inv["amount"]
    if not brand_split:
        for inv in invoices:
            b = inv.get("brand", "Other")
            brand_split[b] = brand_split.get(b, 0) + inv["amount"]

    # recent 6 months trend
    trend = []
    for i in range(5, -1, -1):
        m_start = (datetime.now(timezone.utc) - timedelta(days=30 * (i + 1))).replace(day=1)
        m_end = m_start + timedelta(days=31)
        m_total = sum(inv["amount"] for inv in invoices if inv.get("date") and m_start.isoformat() <= inv["date"] < m_end.isoformat())
        trend.append({"month": m_start.strftime("%b"), "sales": round(m_total, 0)})

    # aging
    now = datetime.now(timezone.utc)
    buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    for inv in invoices:
        if inv.get("status") in {"paid"}:
            continue
        outstanding = inv["amount"] - inv.get("paid_amount", 0)
        try:
            due_dt = datetime.fromisoformat(inv["due_date"])
            days_overdue = (now - due_dt).days
        except Exception:
            days_overdue = 0
        if days_overdue <= 30:
            buckets["0-30"] += outstanding
        elif days_overdue <= 60:
            buckets["31-60"] += outstanding
        elif days_overdue <= 90:
            buckets["61-90"] += outstanding
        else:
            buckets["90+"] += outstanding

    # tasks
    tasks = await db.tasks.find({"assigned_to": user_id, "status": {"$ne": "done"}}, {"_id": 0}).sort("due_date", 1).to_list(20) if user["role"] == "sales" else await db.tasks.find({"status": {"$ne": "done"}}, {"_id": 0}).sort("due_date", 1).to_list(20)

    # priority customers (highest outstanding within assigned)
    priority = sorted(customers, key=lambda c: (-c.get("overdue", 0), -c.get("outstanding", 0)))[:8]

    achievement_pct = (total_achieved / total_target * 100) if total_target else 0
    collection_pct = (total_collected / total_collect_target * 100) if total_collect_target else 0

    return {
        "kpis": {
            "mtd_sales": round(mtd_sales, 0),
            "target": round(total_target, 0),
            "achieved": round(total_achieved, 0),
            "achievement_pct": round(achievement_pct, 1),
            "outstanding": round(total_outstanding, 0),
            "overdue": round(total_overdue, 0),
            "collected": round(total_collected, 0),
            "collection_pct": round(collection_pct, 1),
            "customer_count": len(customers),
            "active_invoices": len([i for i in invoices if i.get("status") != "paid"]),
        },
        "sales_trend": trend,
        "brand_split": [{"brand": k, "value": round(v, 0)} for k, v in brand_split.items()],
        "aging": [{"bucket": k, "amount": round(v, 0)} for k, v in buckets.items()],
        "priority_customers": priority,
        "open_tasks": tasks,
    }


@api.get("/dashboard/accounts")
async def dashboard_accounts(user=Depends(get_current_user)):
    """Accounts panel data."""
    invoices = await db.invoices.find({}, {"_id": 0}).to_list(10000)
    customers = await db.customers.find({}, {"_id": 0}).to_list(5000)

    overdue_invoices = [i for i in invoices if i.get("status") == "overdue"]
    partial = [i for i in invoices if i.get("status") == "partial"]
    unpaid = [i for i in invoices if i.get("status") == "unpaid"]
    paid_today = [i for i in invoices if i.get("status") == "paid"][:10]

    total_outstanding = sum(c.get("outstanding", 0) for c in customers)
    total_overdue = sum(c.get("overdue", 0) for c in customers)

    # GST estimate (18%)
    mtd_invoices = []
    month_start = datetime.now(timezone.utc).replace(day=1).isoformat()
    for i in invoices:
        if i.get("date") and i["date"] >= month_start:
            mtd_invoices.append(i)
    gst_collected = sum(i["amount"] * 0.18 / 1.18 for i in mtd_invoices)

    # daily checklist (mock from notifications)
    checklist = [
        {"id": "1", "title": "Bank reconciliation — HDFC current account", "done": False},
        {"id": "2", "title": f"Send overdue reminders ({len(overdue_invoices)} customers)", "done": False},
        {"id": "3", "title": "Verify credit notes pending approval", "done": True},
        {"id": "4", "title": "Reconcile yesterday's NEFT receipts", "done": False},
        {"id": "5", "title": "GSTR-1 preparation for this month", "done": False},
    ]

    return {
        "kpis": {
            "total_outstanding": round(total_outstanding, 0),
            "total_overdue": round(total_overdue, 0),
            "overdue_count": len(overdue_invoices),
            "unpaid_count": len(unpaid),
            "partial_count": len(partial),
            "gst_collected_mtd": round(gst_collected, 0),
            "mtd_invoice_count": len(mtd_invoices),
        },
        "overdue_invoices": overdue_invoices[:50],
        "partial_invoices": partial[:50],
        "unpaid_invoices": unpaid[:50],
        "recent_paid": paid_today,
        "checklist": checklist,
    }


@api.get("/dashboard/admin")
async def dashboard_admin(user=Depends(require_roles("super_admin", "admin", "manager"))):
    """Admin master dashboard."""
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(500)
    customers = await db.customers.find({}, {"_id": 0}).to_list(5000)
    invoices = await db.invoices.find({}, {"_id": 0}).to_list(10000)
    schemes = await db.schemes.find({"active": True}, {"_id": 0}).to_list(100)

    period = datetime.now(timezone.utc).strftime("%Y-%m")
    targets = await db.targets.find({"period": period}, {"_id": 0}).to_list(100)

    month_start = datetime.now(timezone.utc).replace(day=1).isoformat()
    mtd_sales = sum(i["amount"] for i in invoices if i.get("date") and i["date"] >= month_start)

    # rep leaderboard
    leaderboard = []
    for u in users:
        if u["role"] != "sales":
            continue
        u_targets = [t for t in targets if t["user_id"] == u["id"]]
        target_amt = sum(t["target_amount"] for t in u_targets)
        achieved = sum(t["achieved_amount"] for t in u_targets)
        leaderboard.append({
            "user_id": u["id"],
            "name": u["name"],
            "territory": u.get("territory"),
            "target": target_amt,
            "achieved": achieved,
            "pct": round((achieved / target_amt * 100) if target_amt else 0, 1),
        })
    leaderboard.sort(key=lambda x: -x["pct"])

    return {
        "kpis": {
            "total_users": len(users),
            "sales_users": len([u for u in users if u["role"] == "sales"]),
            "total_customers": len(customers),
            "active_schemes": len(schemes),
            "mtd_sales": round(mtd_sales, 0),
            "total_outstanding": round(sum(c.get("outstanding", 0) for c in customers), 0),
            "total_overdue": round(sum(c.get("overdue", 0) for c in customers), 0),
            "total_invoices": len(invoices),
        },
        "leaderboard": leaderboard,
        "active_schemes": schemes,
    }


# ========== REPORTS ==========
@api.get("/reports/aging")
async def report_aging(user=Depends(get_current_user)):
    invoices = await db.invoices.find({"status": {"$ne": "paid"}}, {"_id": 0}).to_list(10000)
    now = datetime.now(timezone.utc)
    buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    for inv in invoices:
        out = inv["amount"] - inv.get("paid_amount", 0)
        try:
            dt = datetime.fromisoformat(inv["due_date"])
            days = (now - dt).days
        except Exception:
            days = 0
        if days <= 30:
            buckets["0-30"] += out
        elif days <= 60:
            buckets["31-60"] += out
        elif days <= 90:
            buckets["61-90"] += out
        else:
            buckets["90+"] += out
    return [{"bucket": k, "amount": round(v, 0)} for k, v in buckets.items()]


async def _scoped_invoice_filter(db, user) -> dict:
    """Return a Mongo filter that restricts invoices to those owned by the calling sales user.

    Admin/super_admin/manager get an empty filter (full org view).
    """
    if user["role"] != "sales":
        return {}
    cust_ids = await db.customers.distinct("id", {"assigned_to": user["id"]})
    if not cust_ids:
        return {"customer_id": "__no_match__"}
    return {"customer_id": {"$in": cust_ids}}


@api.get("/reports/brand-performance")
async def report_brand_performance(user=Depends(get_current_user)):
    flt = await _scoped_invoice_filter(db, user)
    invoices = await db.invoices.find(flt, {"_id": 0}).to_list(10000)
    brand_totals = {}
    for inv in invoices:
        # Items-level (seed schema)
        for item in inv.get("items", []):
            brand_totals[item["brand"]] = brand_totals.get(item["brand"], 0) + item["amount"]
        # Top-level brand (Zoho-synced invoices)
        b = inv.get("brand")
        if b and not inv.get("items"):
            brand_totals[b] = brand_totals.get(b, 0) + float(inv.get("amount", 0))
    return sorted([{"brand": k, "value": round(v, 0)} for k, v in brand_totals.items()], key=lambda x: -x["value"])


@api.get("/reports/sales-trend")
async def report_sales_trend(user=Depends(get_current_user), months: int = 6):
    flt = await _scoped_invoice_filter(db, user)
    invoices = await db.invoices.find(flt, {"_id": 0}).to_list(20000)
    trend = []
    for i in range(months - 1, -1, -1):
        m_start = (datetime.now(timezone.utc) - timedelta(days=30 * (i + 1))).replace(day=1)
        m_end = m_start + timedelta(days=31)
        total = sum(inv["amount"] for inv in invoices if inv.get("date") and m_start.isoformat() <= inv["date"] < m_end.isoformat())
        coll = sum(inv["paid_amount"] for inv in invoices if inv.get("date") and m_start.isoformat() <= inv["date"] < m_end.isoformat())
        trend.append({"month": m_start.strftime("%b %y"), "sales": round(total, 0), "collected": round(coll, 0)})
    return trend


@api.get("/reports/productivity")
async def report_productivity(user=Depends(get_current_user)):
    users = await db.users.find({"role": "sales"}, {"_id": 0, "password_hash": 0}).to_list(100)
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    targets = await db.targets.find({"period": period}, {"_id": 0}).to_list(100)
    visits = await db.visits.find({}, {"_id": 0}).to_list(5000)
    result = []
    for u in users:
        u_targets = [t for t in targets if t["user_id"] == u["id"]]
        u_visits = [v for v in visits if v["user_id"] == u["id"]]
        target_amt = sum(t["target_amount"] for t in u_targets)
        achieved = sum(t["achieved_amount"] for t in u_targets)
        result.append({
            "user_id": u["id"],
            "name": u["name"],
            "territory": u.get("territory"),
            "visits": len(u_visits),
            "target": target_amt,
            "achieved": achieved,
            "pct": round((achieved / target_amt * 100) if target_amt else 0, 1),
        })
    return sorted(result, key=lambda x: -x["pct"])


# ========== ZOHO SYNC (LIVE) ==========
@api.post("/sync/zoho")
async def trigger_zoho_sync(full: bool = False, current=Depends(require_roles("super_admin", "admin"))):
    """Live Zoho Books sync. Pulls customers, invoices, payments, credit notes.

    Incremental by default (only records changed since the last successful sync) to
    conserve Zoho API credits. Pass ?full=true for a one-off full-org reconcile.
    """
    if zoho_creds_present():
        return await sync_zoho(db, use_checkpoint=not full)
    try:
        await refresh_customer_aggregates(db)
        log = {
            "id": new_id(),
            "started_at": now_iso(),
            "status": "completed",
            "type": "aggregate_refresh",
            "message": "Local aggregate refresh (Zoho credentials not configured yet).",
        }
    except Exception as e:
        log = {"id": new_id(), "started_at": now_iso(), "status": "failed", "message": str(e)}
    await db.sync_logs.insert_one(log)
    log.pop("_id", None)
    return log


@api.get("/sync/zoho/status")
async def zoho_status(current=Depends(require_roles("super_admin", "admin"))):
    cfg = await db.config.find_one({"key": "zoho"}, {"_id": 0}) or {}
    return {
        "credentials_present": zoho_creds_present(),
        "region": cfg.get("region"),
        "organization_id": cfg.get("organization_id"),
        "organization_name": cfg.get("organization_name"),
        "all_organizations": cfg.get("organizations", []),
        "detected_at": cfg.get("detected_at"),
    }


@api.post("/sync/zoho/detect")
async def zoho_detect(current=Depends(require_roles("super_admin", "admin"))):
    """Probe regions, detect org id, save to config."""
    return await detect_region_and_org(db)


@api.post("/import/historical")
async def import_historical_endpoint(force: bool = False, current=Depends(require_roles("super_admin", "admin"))):
    """Import 5 Excel files from /app/data/imports/. Idempotent unless force=true."""
    return await import_historical(db, force=force)


@api.post("/import/mapping")
async def import_mapping_endpoint(current=Depends(require_roles("super_admin", "admin"))):
    """Apply Nalanda secondary-drive mapping: tier, beat_days, salesperson assignment."""
    return await apply_mapping(db)


# ========== UNIVERSAL DATA UPLOAD CENTER ==========
@api.post("/admin/upload/customers")
async def admin_upload_customers(file: UploadFile = File(...), current=Depends(require_roles("super_admin", "admin"))):
    """Upload/update customers. See /api/admin/upload-template/customers for column spec."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty file")
    return await svc_upload_customers(db, content, file.filename or "")


@api.post("/admin/upload/beat-plans")
async def admin_upload_beats(file: UploadFile = File(...), current=Depends(require_roles("super_admin", "admin"))):
    """Upload beat-day plans (customer_name → beat_days)."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty file")
    return await svc_upload_beats(db, content, file.filename or "")


@api.post("/admin/upload/salesperson-mapping")
async def admin_upload_sp_mapping(file: UploadFile = File(...), current=Depends(require_roles("super_admin", "admin"))):
    """Map customers to salespersons (and optionally tier/beat_days/target)."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty file")
    return await svc_upload_sp_mapping(db, content, file.filename or "")


@api.get("/admin/upload-template/{kind}")
async def admin_template(kind: str, current=Depends(require_roles("super_admin", "admin"))):
    csv = get_template_csv(kind)
    if not csv:
        raise HTTPException(status_code=404, detail=f"unknown template: {kind}")
    return Response(content=csv, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={kind}_template.csv"})


@api.post("/admin/backfill-addresses")
async def admin_backfill_addresses(current=Depends(require_roles("super_admin", "admin")),
                                   max_concurrent: int = 4, batch_delay: float = 2.0,
                                   limit: Optional[int] = None):
    """Backfill billing addresses from Zoho for customers still showing default city.

    Runs synchronously; may take 1-5 minutes for full org. Use ?limit=100 to test on a sample.
    """
    return await svc_backfill_addresses(db, max_concurrent=max_concurrent,
                                        batch_delay=batch_delay, limit=limit)


# ========== BEAT DAY TODAY ==========
@api.get("/beat/today")
async def beat_today(user=Depends(get_current_user), user_id: Optional[str] = None, limit: int = 12):
    """Daily beat plan — which customers should this salesperson visit TODAY based on beat_days schedule.

    Returns at most `limit` stops (default 12). Stops are ranked by tier × overdue × days-since-visit.
    """
    target_id = user["id"] if user["role"] == "sales" or not user_id else user_id
    target_user = await db.users.find_one({"id": target_id}, {"_id": 0, "password_hash": 0}) or user
    q = {}
    if target_user.get("role") == "sales":
        q["assigned_to"] = target_id
    elif user_id:
        q["assigned_to"] = user_id
    customers = await db.customers.find(q, {"_id": 0}).to_list(5000)
    plan = build_today_beat(customers)
    # Apply max cap
    if isinstance(plan.get("stops"), list) and limit and limit > 0:
        all_stops = plan["stops"]
        plan["stops"] = all_stops[:limit]
        plan["summary"]["total_available"] = len(all_stops)
        plan["summary"]["limit"] = limit
    return plan


@api.post("/beat/visit")
async def mark_beat_visit(payload: dict, user=Depends(get_current_user)):
    """Mark a customer as visited today (creates a visit record + updates last_visit_date)."""
    customer_id = payload.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="customer_id required")
    now = datetime.now(timezone.utc)
    visit = {
        "id": new_id(),
        "user_id": user["id"],
        "customer_id": customer_id,
        "date": now.isoformat(),
        "duration_minutes": payload.get("duration_minutes", 20),
        "notes": payload.get("notes", ""),
        "lat": payload.get("lat"),
        "lng": payload.get("lng"),
        "outcome": payload.get("outcome", "followup"),
        "created_at": now.isoformat(),
    }
    await db.visits.insert_one(visit)
    await db.customers.update_one({"id": customer_id}, {"$set": {"last_visit_date": now.isoformat()}})
    visit.pop("_id", None)
    return visit


@api.get("/sync/logs")
async def sync_logs(current=Depends(require_roles("super_admin", "admin"))):
    logs = await db.sync_logs.find({}, {"_id": 0}).sort("started_at", -1).to_list(50)
    return logs


# ========== LOCATION & ATTENDANCE (Silent GPS) ==========
@api.post("/location/ping")
async def location_ping(body: LocationPing, user=Depends(get_current_user)):
    """Silent location ping from the client. Used for attendance + admin live map.
    No notifications are sent. Frontend collects this in background without user-facing UI."""
    now = datetime.now(timezone.utc)
    ts = body.timestamp or now.isoformat()
    doc = {
        "id": new_id(),
        "user_id": user["id"],
        "lat": body.lat,
        "lng": body.lng,
        "accuracy": body.accuracy,
        "speed": body.speed,
        "battery": body.battery,
        "timestamp": ts,
        "created_at": now.isoformat(),
    }
    await db.location_pings.insert_one(doc)

    # Auto attendance — first ping of day = check-in; latest ping = check-out
    date_key = now.strftime("%Y-%m-%d")
    existing = await db.attendance.find_one({"user_id": user["id"], "date": date_key})
    if not existing:
        await db.attendance.insert_one({
            "id": new_id(),
            "user_id": user["id"],
            "date": date_key,
            "check_in": ts,
            "check_in_lat": body.lat,
            "check_in_lng": body.lng,
            "check_out": ts,
            "check_out_lat": body.lat,
            "check_out_lng": body.lng,
            "ping_count": 1,
        })
    else:
        await db.attendance.update_one(
            {"user_id": user["id"], "date": date_key},
            {"$set": {
                "check_out": ts,
                "check_out_lat": body.lat,
                "check_out_lng": body.lng,
            }, "$inc": {"ping_count": 1}}
        )
    return {"ok": True}


@api.get("/location/latest")
async def location_latest(user=Depends(require_roles("super_admin", "admin", "manager")), user_id: Optional[str] = None):
    """Admin/manager view of latest locations for all sales users."""
    if user_id:
        ping = await db.location_pings.find({"user_id": user_id}, {"_id": 0}).sort("timestamp", -1).limit(1).to_list(1)
        return ping[0] if ping else {}
    # Aggregate latest per user
    sales = await db.users.find({"role": "sales", "active": True}, {"_id": 0, "id": 1, "name": 1, "territory": 1}).to_list(100)
    result = []
    for u in sales:
        ping = await db.location_pings.find({"user_id": u["id"]}, {"_id": 0}).sort("timestamp", -1).limit(1).to_list(1)
        if ping:
            result.append({**u, **ping[0]})
        else:
            result.append({**u, "lat": None, "lng": None, "timestamp": None})
    return result


@api.get("/attendance")
async def list_attendance(
    user=Depends(get_current_user),
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    q = {}
    if user["role"] == "sales":
        q["user_id"] = user["id"]
    elif user_id:
        q["user_id"] = user_id
    if date_from or date_to:
        q["date"] = {}
        if date_from:
            q["date"]["$gte"] = date_from
        if date_to:
            q["date"]["$lte"] = date_to
    records = await db.attendance.find(q, {"_id": 0}).sort("date", -1).to_list(500)
    return records


@api.get("/attendance/today")
async def attendance_today(current=Depends(require_roles("super_admin", "admin", "manager"))):
    """Today's attendance roll-call for admin."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sales = await db.users.find({"role": "sales", "active": True}, {"_id": 0, "password_hash": 0}).to_list(100)
    records = await db.attendance.find({"date": today}, {"_id": 0}).to_list(500)
    rec_by_user = {r["user_id"]: r for r in records}
    out = []
    for u in sales:
        r = rec_by_user.get(u["id"])
        out.append({
            "user_id": u["id"],
            "name": u["name"],
            "territory": u.get("territory"),
            "checked_in": bool(r),
            "check_in": r.get("check_in") if r else None,
            "last_ping": r.get("check_out") if r else None,
            "ping_count": r.get("ping_count", 0) if r else 0,
        })
    return out


# ========== AI ROUTE & PERFORMANCE (Live data) ==========
@api.get("/ai/route-plan")
async def ai_route_plan(user=Depends(get_current_user), user_id: Optional[str] = None, max_stops: int = 10):
    """AI-prioritised route plan using LIVE customer data (outstanding, overdue, last-visit)."""
    target_id = user["id"] if user["role"] == "sales" or not user_id else user_id
    target_user = await db.users.find_one({"id": target_id}, {"_id": 0, "password_hash": 0}) or user
    # Their assigned customers (if sales) else all
    if target_user.get("role") == "sales":
        customers = await db.customers.find({"assigned_to": target_id}, {"_id": 0}).to_list(500)
    else:
        customers = await db.customers.find({}, {"_id": 0}).to_list(2000)
    plan = await generate_route_plan(target_user, customers, max_stops=max_stops)
    return plan


@api.get("/ai/performance")
async def ai_performance(user=Depends(get_current_user), user_id: Optional[str] = None):
    """AI performance analysis from LIVE 30-day data."""
    target_id = user["id"] if user["role"] == "sales" or not user_id else user_id
    target_user = await db.users.find_one({"id": target_id}, {"_id": 0, "password_hash": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    period = datetime.now(timezone.utc).strftime("%Y-%m")
    target = await db.targets.find_one({"user_id": target_id, "period": period}, {"_id": 0})

    cust_ids = [c["id"] for c in await db.customers.find({"assigned_to": target_id}, {"_id": 0, "id": 1}).to_list(1000)]
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    invoices = await db.invoices.find({"customer_id": {"$in": cust_ids}, "date": {"$gte": thirty_days_ago}}, {"_id": 0}).to_list(2000)
    payments = await db.payments.find({"customer_id": {"$in": cust_ids}, "date": {"$gte": thirty_days_ago}}, {"_id": 0}).to_list(2000)
    visits = await db.visits.find({"user_id": target_id, "date": {"$gte": thirty_days_ago}}, {"_id": 0}).to_list(500)

    return await generate_performance_analysis(target_user, target, invoices, payments, visits)


# ========== VIEWER (Brand partner) DASHBOARD ==========
@api.get("/dashboard/viewer")
async def dashboard_viewer(user=Depends(get_current_user)):
    """Restricted dashboard for external viewers (e.g. Boat brand partner).
    Returns ONLY day-wise total sales of allowed brands. No customer names, no individual invoices."""
    perms = user_permissions(user)
    allowed_brands = perms.get("brands") or []
    q = {}
    if allowed_brands:
        q["brand"] = {"$in": allowed_brands}
    # last 30 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    q["date"] = {"$gte": cutoff}
    invoices = await db.invoices.find(q, {"_id": 0}).to_list(10000)

    # Group by date + brand → totals only
    by_day = {}
    for inv in invoices:
        d = (inv.get("date") or "")[:10]
        if not d:
            continue
        by_day.setdefault(d, {})
        b = inv.get("brand", "Other")
        by_day[d][b] = by_day[d].get(b, 0) + inv.get("amount", 0)

    days_sorted = sorted(by_day.keys())
    rows = []
    for d in days_sorted:
        row = {"date": d, "total": round(sum(by_day[d].values()), 0)}
        for b, v in by_day[d].items():
            row[b] = round(v, 0)
        rows.append(row)

    # Aggregate totals
    grand_total = sum(r["total"] for r in rows)
    brand_totals = {}
    for inv in invoices:
        b = inv.get("brand", "Other")
        brand_totals[b] = brand_totals.get(b, 0) + inv.get("amount", 0)

    return {
        "scope": {
            "brands": allowed_brands or ["All"],
            "view_scope": perms.get("view_scope"),
            "days": 30,
        },
        "totals": {
            "grand_total": round(grand_total, 0),
            "day_count": len(rows),
            "avg_daily": round(grand_total / max(1, len(rows)), 0),
            "by_brand": [{"brand": k, "value": round(v, 0)} for k, v in brand_totals.items()],
        },
        "daily": rows,
    }


# ========== HEALTH ==========
@api.get("/health")
async def health():
    return {"status": "ok", "time": now_iso()}


@api.get("/")
async def root():
    return {"service": "nalanda-erp", "status": "running"}


app.include_router(api)
