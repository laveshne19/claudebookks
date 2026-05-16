"""Universal data upload service.

Admin can upload Excel/CSV files for:
- customers (with sector/area, salesperson, tier, beat_days)
- beat_plans (customer_name, beat_days)
- salesperson_mapping (customer_name → salesperson email/name)
- schemes (already handled in scheme_service.py)

All uploaders use fuzzy name match for idempotent updates.
"""
import io
import csv
import logging
from datetime import datetime, timezone
from difflib import SequenceMatcher

import pandas as pd

from address_utils import normalize_area, state_from_gstin
from models import new_id, now_iso

logger = logging.getLogger(__name__)


# --------------------- Parsing helpers ---------------------
def _parse_rows(file_bytes: bytes, filename: str) -> list[dict]:
    name = (filename or "").lower()
    if name.endswith(".csv"):
        text = file_bytes.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        rows = [dict(r) for r in reader]
    else:
        df = pd.read_excel(io.BytesIO(file_bytes))
        df.columns = [str(c).strip().lower() for c in df.columns]
        rows = df.to_dict(orient="records")
    out = []
    for r in rows:
        clean = {}
        for k, v in r.items():
            if v is None:
                continue
            if isinstance(v, float) and pd.isna(v):
                continue
            clean[str(k).strip().lower()] = v
        out.append(clean)
    return out


def _norm(s) -> str:
    return str(s or "").strip().lower()


def _fuzzy_find_customer(name: str, all_customers: list[dict]) -> dict | None:
    """Find the best customer match for a given name."""
    if not name:
        return None
    target = _norm(name)
    # exact match first
    for c in all_customers:
        if _norm(c.get("name")) == target:
            return c
    # contains
    cands = [c for c in all_customers if target in _norm(c.get("name")) or _norm(c.get("name")) in target]
    if len(cands) == 1:
        return cands[0]
    # fuzzy (only on the contains-shortlist for performance)
    pool = cands if cands else all_customers
    best, best_score = None, 0.0
    for c in pool:
        score = SequenceMatcher(None, target, _norm(c.get("name"))).ratio()
        if score > best_score:
            best, best_score = c, score
    if best and best_score >= 0.82:
        return best
    return None


# --------------------- Uploaders ---------------------
async def upload_customers(db, file_bytes: bytes, filename: str) -> dict:
    """Upload/update customer records.

    Recognised columns (any subset; case-insensitive):
      required: name
      optional: code, phone, email, gstin, address, area, sector, city, state, zip,
                tier, beat_days, salesperson (name or email), monthly_target,
                l3m_avg_value, brand_preferences (comma-sep), credit_limit,
                lat, lng, outstanding
    """
    rows = _parse_rows(file_bytes, filename)
    if not rows:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": ["empty file"]}

    # Build salesperson lookup once
    users = await db.users.find({}, {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}).to_list(500)
    sp_by_name = {_norm(u["name"]): u["id"] for u in users}
    sp_by_email = {_norm(u["email"]): u["id"] for u in users}

    customers = await db.customers.find({}, {"_id": 0, "id": 1, "name": 1, "zoho_contact_id": 1, "code": 1}).to_list(50000)

    created = updated = skipped = 0
    errors: list[str] = []

    for i, row in enumerate(rows, start=2):
        try:
            name = str(row.get("name") or row.get("customer") or row.get("customer_name") or "").strip()
            if not name:
                skipped += 1
                continue

            doc: dict = {"name": name}

            # Address / sector
            sector = str(row.get("sector") or "").strip()
            area = str(row.get("area") or row.get("locality") or "").strip()
            city = str(row.get("city") or "").strip()
            address = str(row.get("address") or "").strip()
            if sector:
                doc["area"] = f"Sector {sector}" if sector.lower().replace("sector", "").strip() == sector.lower() and sector.isdigit() else sector
            elif area:
                doc["area"] = area
            else:
                derived = normalize_area(address=address, city=city)
                if derived != "—":
                    doc["area"] = derived
            if city:
                doc["city"] = city
            if address:
                doc["address"] = address
            for k in ("state", "zip"):
                v = row.get(k)
                if v is not None and str(v).strip():
                    doc[k] = str(v).strip()
            if not doc.get("state") and row.get("gstin"):
                s = state_from_gstin(str(row["gstin"]))
                if s:
                    doc["state"] = s

            # Contact
            for k in ("code", "phone", "email", "gstin", "contact_person"):
                v = row.get(k)
                if v is not None and str(v).strip():
                    doc[k] = str(v).strip()

            # Tier / beat / target
            for k in ("tier", "beat_days"):
                v = row.get(k)
                if v is not None and str(v).strip():
                    doc[k] = str(v).strip()
            if doc.get("tier"):
                doc["tier"] = doc["tier"].upper()
            for k in ("monthly_target", "l3m_avg_value", "credit_limit", "outstanding", "lat", "lng"):
                v = row.get(k)
                if v is not None and str(v).strip():
                    try:
                        doc[k] = float(v)
                    except Exception:
                        pass

            # Salesperson resolution
            sp_raw = str(row.get("salesperson") or row.get("sales_person") or row.get("assigned_to") or "").strip()
            if sp_raw:
                sid = sp_by_email.get(_norm(sp_raw)) or sp_by_name.get(_norm(sp_raw))
                if sid:
                    doc["assigned_to"] = sid
                else:
                    errors.append(f"Row {i}: salesperson '{sp_raw}' not found")

            # Brand preferences
            bp = row.get("brand_preferences") or row.get("brands")
            if bp:
                doc["brand_preferences"] = [b.strip() for b in str(bp).split(",") if b.strip()]

            # Match existing
            existing = _fuzzy_find_customer(name, customers)
            if existing:
                await db.customers.update_one({"id": existing["id"]}, {"$set": doc})
                updated += 1
            else:
                doc.update({
                    "id": new_id(),
                    "code": doc.get("code") or f"UP-{new_id()[:6].upper()}",
                    "brand_preferences": doc.get("brand_preferences", []),
                    "credit_risk_score": 50,
                    "payment_behaviour_score": 50,
                    "overdue": 0.0,
                    "total_purchases": 0.0,
                    "source": "uploaded",
                    "created_at": now_iso(),
                })
                await db.customers.insert_one(doc)
                created += 1
        except Exception as e:
            errors.append(f"Row {i}: {e}")
            skipped += 1

    return {"created": created, "updated": updated, "skipped": skipped,
            "errors": errors[:50], "total_rows": len(rows)}


async def upload_beat_plans(db, file_bytes: bytes, filename: str) -> dict:
    """Upload beat_days for existing customers.

    Columns: name (or customer_name), beat_days
    """
    rows = _parse_rows(file_bytes, filename)
    if not rows:
        return {"updated": 0, "not_found": 0, "errors": ["empty file"]}
    customers = await db.customers.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(50000)
    updated = not_found = 0
    errors: list[str] = []
    for i, row in enumerate(rows, start=2):
        name = str(row.get("name") or row.get("customer") or row.get("customer_name") or "").strip()
        days = str(row.get("beat_days") or row.get("beat") or row.get("days") or "").strip()
        if not name or not days:
            continue
        c = _fuzzy_find_customer(name, customers)
        if c:
            await db.customers.update_one({"id": c["id"]}, {"$set": {"beat_days": days}})
            updated += 1
        else:
            not_found += 1
            errors.append(f"Row {i}: customer '{name}' not found")
    return {"updated": updated, "not_found": not_found, "errors": errors[:50], "total_rows": len(rows)}


async def upload_salesperson_mapping(db, file_bytes: bytes, filename: str) -> dict:
    """Map customers to salespersons. Columns: name, salesperson (name or email).

    Optional: tier, beat_days, monthly_target (also applied if present).
    """
    rows = _parse_rows(file_bytes, filename)
    users = await db.users.find({}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(500)
    sp_by_name = {_norm(u["name"]): u["id"] for u in users}
    sp_by_email = {_norm(u["email"]): u["id"] for u in users}
    customers = await db.customers.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(50000)
    updated = not_found_cust = not_found_sp = 0
    errors: list[str] = []
    for i, row in enumerate(rows, start=2):
        name = str(row.get("name") or row.get("customer") or row.get("customer_name") or "").strip()
        sp_raw = str(row.get("salesperson") or row.get("sales_person") or row.get("assigned_to") or "").strip()
        if not name or not sp_raw:
            continue
        sid = sp_by_email.get(_norm(sp_raw)) or sp_by_name.get(_norm(sp_raw))
        if not sid:
            not_found_sp += 1
            errors.append(f"Row {i}: salesperson '{sp_raw}' not found")
            continue
        c = _fuzzy_find_customer(name, customers)
        if not c:
            not_found_cust += 1
            errors.append(f"Row {i}: customer '{name}' not found")
            continue
        upd = {"assigned_to": sid}
        for k in ("tier", "beat_days"):
            v = row.get(k)
            if v is not None and str(v).strip():
                upd[k] = str(v).strip().upper() if k == "tier" else str(v).strip()
        for k in ("monthly_target", "l3m_avg_value"):
            v = row.get(k)
            if v is not None and str(v).strip():
                try:
                    upd[k] = float(v)
                except Exception:
                    pass
        await db.customers.update_one({"id": c["id"]}, {"$set": upd})
        updated += 1
    return {
        "updated": updated,
        "not_found_customer": not_found_cust,
        "not_found_salesperson": not_found_sp,
        "errors": errors[:50],
        "total_rows": len(rows),
    }


# --------------------- Template generator ---------------------
TEMPLATES = {
    "customers": {
        "required": ["name"],
        "optional": ["code", "phone", "email", "gstin", "address", "sector", "area",
                     "city", "state", "zip", "tier", "beat_days", "salesperson",
                     "monthly_target", "l3m_avg_value", "credit_limit",
                     "brand_preferences", "lat", "lng"],
        "example": {
            "name": "Bharat Electronics", "code": "BE-001", "phone": "9999999999",
            "gstin": "04ABCDE1234F1Z5", "address": "Booth 12", "sector": "22",
            "city": "Chandigarh", "tier": "GOLD", "beat_days": "Mon, Thu",
            "salesperson": "navneet@nalanda.com", "monthly_target": 50000,
        },
    },
    "beat_plans": {
        "required": ["name", "beat_days"],
        "optional": [],
        "example": {"name": "Bharat Electronics", "beat_days": "Mon, Thu"},
    },
    "salesperson_mapping": {
        "required": ["name", "salesperson"],
        "optional": ["tier", "beat_days", "monthly_target", "l3m_avg_value"],
        "example": {"name": "Bharat Electronics", "salesperson": "navneet@nalanda.com",
                    "tier": "GOLD", "beat_days": "Mon, Thu", "monthly_target": 50000},
    },
}


def get_template_csv(kind: str) -> str:
    spec = TEMPLATES.get(kind)
    if not spec:
        return ""
    cols = spec["required"] + spec["optional"]
    example = spec["example"]
    lines = [",".join(cols)]
    lines.append(",".join(str(example.get(c, "")) for c in cols))
    return "\n".join(lines)
