"""Excel importer for historical 2025-26 sales orders from Nalanda's 5 salespeople.

Each file:
  Row 0 = currency banner
  Row 1 = column headers (Vch Type / Invoice No / Invoice Date / Company / ... / Product Title / ...)
  Row 2+ = data. When an SO has multiple line items, subsequent rows have ONLY the product
           columns; the header columns must be carried forward.

Result of import:
  - Creates 5 sales users (rohit, sarabjeet, navneet, davinder, atinder)
  - Creates/updates customers (by Company Name)
  - Creates one invoice per (salesperson, SO number) with all line items rolled up
  - Brand detected from Product Group; falls back to title prefix
  - Idempotent: re-running the importer skips already-imported SOs (matched on (salesperson, so_number))
"""
import os
import re
import logging
from datetime import datetime, timezone
from typing import Optional
import openpyxl
from auth import hash_password
from models import new_id, now_iso

logger = logging.getLogger(__name__)

DATA_DIR = "/app/data/imports"

SALESPEOPLE = [
    {"file": "rohit.xlsx",     "email": "rohit@nalanda.com",     "name": "Rohit",      "territory": "Rohit Beat"},
    {"file": "sarabjeet.xlsx", "email": "sarabjeet@nalanda.com", "name": "Sarabjeet",  "territory": "Sarabjeet Beat"},
    {"file": "navneet.xlsx",   "email": "navneet@nalanda.com",   "name": "Navneet",    "territory": "Navneet Beat"},
    {"file": "davinder.xlsx",  "email": "davinder@nalanda.com",  "name": "Davinder",   "territory": "Davinder Beat"},
    {"file": "atinder.xlsx",   "email": "atinder@nalanda.com",   "name": "Atinder",    "territory": "Atinder Beat"},
]

BRAND_HINTS = {
    "boat": "Boat",
    "boAt": "Boat",
    "fireboltt": "Fireboltt",
    "fire-boltt": "Fireboltt",
    "noise": "Noise",
    "logitech": "Logitech",
    "amazon": "Amazon",
    "swiss military": "Swiss Military",
    "mivi": "Mivi",
    "toreto": "Toreto",
    "portronics": "Portronics",
    "potronics": "Portronics",
    "ambrane": "Ambrane",
    "intex": "Intex",
    "syska": "Syska",
    "philips": "Philips",
    "jbl": "JBL",
    "samsung": "Samsung",
}


def _detect_brand(product_group: Optional[str], product_title: Optional[str]) -> str:
    for src in (product_group, product_title):
        if not src:
            continue
        low = str(src).lower()
        for hint, label in BRAND_HINTS.items():
            if hint in low:
                return label
    # First token of title
    if product_title:
        return str(product_title).split()[0].title()
    return "Other"


def _parse_date(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=timezone.utc).isoformat()
    s = str(val).strip()
    for fmt in ("%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return None


def _to_float(v, default=0.0):
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _normalise_header(h: str) -> str:
    if not h:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", str(h).strip().lower()).strip("_")


async def _ensure_user(db, sp: dict) -> str:
    existing = await db.users.find_one({"email": sp["email"]})
    if existing:
        return existing["id"]
    doc = {
        "id": new_id(),
        "email": sp["email"],
        "password_hash": hash_password("Sales@123"),
        "name": sp["name"],
        "role": "sales",
        "phone": "",
        "territory": sp["territory"],
        "active": True,
        "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    return doc["id"]


async def _ensure_customer(db, company: str, user_id: str) -> str:
    company = (company or "").strip()
    if not company:
        return None
    existing = await db.customers.find_one({"name": company})
    if existing:
        # If unassigned, assign to importing user
        if not existing.get("assigned_to"):
            await db.customers.update_one({"id": existing["id"]}, {"$set": {"assigned_to": user_id}})
        return existing["id"]
    doc = {
        "id": new_id(),
        "name": company,
        "code": f"NAL-{abs(hash(company)) % 100000:05d}",
        "area": "Imported",
        "city": "—",
        "state": "—",
        "contact_person": None,
        "phone": None,
        "email": None,
        "gstin": None,
        "credit_limit": 0.0,
        "brand_preferences": [],
        "assigned_to": user_id,
        "lat": None,
        "lng": None,
        "outstanding": 0.0,
        "overdue": 0.0,
        "last_payment_date": None,
        "last_visit_date": None,
        "last_order_date": None,
        "total_purchases": 0.0,
        "credit_risk_score": 50,
        "payment_behaviour_score": 50,
        "created_at": now_iso(),
        "source": "excel_2025_26",
    }
    await db.customers.insert_one(doc)
    return doc["id"]


def _read_workbook(path: str):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    # Find header row (look for a row that has 'Vch Type' or similar)
    header_idx = None
    for i, r in enumerate(rows):
        if r and any(isinstance(c, str) and "Vch Type" in c for c in r):
            header_idx = i
            break
    if header_idx is None:
        header_idx = 1
    headers = [_normalise_header(c) for c in rows[header_idx]]
    return headers, rows[header_idx + 1:]


def _col(headers, *names):
    """Return index of first matching column name (normalised)."""
    for n in names:
        n = _normalise_header(n)
        if n in headers:
            return headers.index(n)
    return None


async def import_all(db, force: bool = False) -> dict:
    summary = {"users": 0, "customers_created": 0, "invoices_created": 0, "line_items": 0, "files": []}

    for sp in SALESPEOPLE:
        path = os.path.join(DATA_DIR, sp["file"])
        if not os.path.exists(path):
            summary["files"].append({"file": sp["file"], "status": "missing"})
            continue

        user_id = await _ensure_user(db, sp)
        summary["users"] += 1

        headers, data_rows = _read_workbook(path)
        c_vch = _col(headers, "vch_type")
        c_so = _col(headers, "invoice_no", "sale_order_no", "so_no", "voucher_no")
        c_date = _col(headers, "invoice_date", "sale_order_date", "so_date", "date")
        c_company = _col(headers, "company_name", "customer_name", "party_name")
        c_taxable = _col(headers, "taxable_value_total", "taxable_value")
        c_grand = _col(headers, "grand_total", "total")
        c_qty = _col(headers, "quantity_total", "quantity")
        c_title = _col(headers, "product_title", "item_name")
        c_price = _col(headers, "product_price", "rate")
        c_pqty = _col(headers, "product_quantity", "item_quantity")
        c_ptax = _col(headers, "product_taxable", "item_taxable")
        c_ptot = _col(headers, "product_total", "item_total")
        c_group = _col(headers, "product_group", "brand")
        c_hsn = _col(headers, "product_hsn", "hsn")

        if c_so is None or c_company is None or c_title is None:
            summary["files"].append({"file": sp["file"], "status": "header_mismatch", "headers": headers})
            continue

        # Group line items by SO
        current_so = None
        current_date = None
        current_company = None
        current_taxable = None
        current_grand = None
        current_qty = None
        so_buckets = {}  # so_no -> {"meta": {...}, "items": [...]}

        for r in data_rows:
            if not r:
                continue
            so_val = r[c_so] if c_so < len(r) else None
            if so_val not in (None, ""):
                current_so = str(so_val).strip()
                current_date = _parse_date(r[c_date]) if c_date is not None else None
                current_company = (str(r[c_company]).strip() if c_company is not None and r[c_company] else None)
                current_taxable = _to_float(r[c_taxable]) if c_taxable is not None else 0
                current_grand = _to_float(r[c_grand]) if c_grand is not None else 0
                current_qty = _to_float(r[c_qty]) if c_qty is not None else 0
                if current_so not in so_buckets:
                    so_buckets[current_so] = {
                        "meta": {
                            "date": current_date,
                            "company": current_company,
                            "taxable": current_taxable,
                            "grand": current_grand,
                            "qty": current_qty,
                        },
                        "items": [],
                    }

            if not current_so:
                continue

            title = r[c_title] if c_title is not None and c_title < len(r) else None
            if not title:
                continue
            group = r[c_group] if c_group is not None and c_group < len(r) else None
            brand = _detect_brand(group, title)
            unit_price = _to_float(r[c_price]) if c_price is not None else 0
            qty = _to_float(r[c_pqty]) if c_pqty is not None else 0
            taxable = _to_float(r[c_ptax]) if c_ptax is not None else 0
            total = _to_float(r[c_ptot]) if c_ptot is not None else taxable
            hsn = (str(r[c_hsn]).strip() if c_hsn is not None and r[c_hsn] is not None else None)

            so_buckets[current_so]["items"].append({
                "sku": hsn or f"SKU-{abs(hash(str(title))) % 100000}",
                "product": str(title),
                "brand": brand,
                "qty": int(qty) if qty else 0,
                "unit_price": unit_price,
                "amount": total or taxable,
            })

        # Insert invoices
        for so_no, bucket in so_buckets.items():
            meta = bucket["meta"]
            if not meta["company"] or not meta["date"]:
                continue
            cust_id = await _ensure_customer(db, meta["company"], user_id)
            if not cust_id:
                continue

            invoice_no = f"SO-{sp['name'][:3].upper()}-{so_no}"
            # idempotency
            existing = await db.invoices.find_one({"invoice_no": invoice_no})
            if existing and not force:
                continue

            # primary brand = highest-value brand in items
            brand_tot = {}
            for it in bucket["items"]:
                brand_tot[it["brand"]] = brand_tot.get(it["brand"], 0) + it["amount"]
            primary_brand = max(brand_tot, key=brand_tot.get) if brand_tot else "Other"

            # mark all old invoices as paid (historical, FY 2025-26)
            inv = {
                "id": new_id(),
                "invoice_no": invoice_no,
                "customer_id": cust_id,
                "date": meta["date"],
                "due_date": meta["date"],
                "items": bucket["items"],
                "amount": meta["grand"] or sum(i["amount"] for i in bucket["items"]),
                "paid_amount": meta["grand"] or sum(i["amount"] for i in bucket["items"]),
                "status": "paid",
                "brand": primary_brand,
                "created_at": now_iso(),
                "source": "excel_2025_26",
                "salesperson_id": user_id,
            }
            if existing and force:
                await db.invoices.update_one({"invoice_no": invoice_no}, {"$set": inv})
            else:
                await db.invoices.insert_one(inv)
                summary["invoices_created"] += 1
            summary["line_items"] += len(bucket["items"])

            # update customer brand_preferences
            cust = await db.customers.find_one({"id": cust_id}, {"_id": 0})
            if cust:
                prefs = set(cust.get("brand_preferences") or [])
                prefs.update(brand_tot.keys())
                # keep top 6
                await db.customers.update_one({"id": cust_id}, {"$set": {"brand_preferences": list(prefs)[:6]}})

        summary["files"].append({"file": sp["file"], "status": "ok", "user": sp["name"], "sos": len(so_buckets)})

    # Refresh aggregates
    try:
        from scheduler import refresh_customer_aggregates
        await refresh_customer_aggregates(db)
    except Exception as e:
        logger.exception("Aggregate refresh after import failed: %s", e)

    # Count created customers
    summary["customers_created"] = await db.customers.count_documents({"source": "excel_2025_26"})
    return summary
