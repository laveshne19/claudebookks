"""Apply Nalanda secondary-drive mapping to customers.

Maps each outlet → salesperson + tier + beat_days + MTD target + L3M average value.
Matches customers by fuzzy outlet name; updates assigned_to, tier, beat_days, target_amount.
"""
import os
import logging
import re
from datetime import datetime, timezone
import openpyxl
from models import new_id, now_iso

logger = logging.getLogger(__name__)

MAPPING_FILE = "/app/data/imports/mapping.xlsx"


def _normalize(s: str) -> str:
    """Aggressive normalize for matching: lowercase, strip punctuation/spaces."""
    if not s:
        return ""
    s = str(s).lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


async def apply_mapping(db) -> dict:
    if not os.path.exists(MAPPING_FILE):
        return {"ok": False, "error": "mapping.xlsx not found"}

    wb = openpyxl.load_workbook(MAPPING_FILE, read_only=True, data_only=True)
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]

    # column indices
    def col(*names):
        for n in names:
            ni = [str(h).strip().lower() if h else "" for h in header]
            for i, h in enumerate(ni):
                if any(x in h for x in [name.lower() for name in (n if isinstance(n, list) else [n])]):
                    return i
        return None

    c_outlet = 1  # Outlet Name
    c_tier = 3    # Retailer Cate Final
    c_l3m = 2     # L3M Average Value
    c_mtd_tgt = 8  # MTD Tgt
    c_sp = 13      # Salesperson
    c_beat = 16    # Beat Days

    # Pre-load users by first-name for matching
    users = await db.users.find({"role": "sales", "active": True}, {"_id": 0}).to_list(500)
    name_to_user = {}
    for u in users:
        first = (u.get("name") or "").split()[0].strip().lower()
        if first:
            name_to_user[first] = u["id"]
        zsp_email = (u.get("zoho_salesperson_email") or u.get("email") or "").split("@")[0].lower()
        if zsp_email:
            name_to_user[zsp_email] = u["id"]

    # Pre-load customers and build normalized name index
    customers = await db.customers.find({}, {"_id": 0}).to_list(20000)
    norm_idx = {}
    for c in customers:
        norm = _normalize(c.get("name", ""))
        if norm:
            norm_idx.setdefault(norm, []).append(c["id"])

    stats = {
        "rows_processed": 0,
        "customers_assigned": 0,
        "customers_created": 0,
        "salespersons_missing": set(),
        "unmatched_outlets": 0,
        "tiers_set": {},
    }

    for r in rows[1:]:
        if not r or not r[c_outlet]:
            continue
        stats["rows_processed"] += 1

        outlet = str(r[c_outlet]).strip()
        tier = (str(r[c_tier]).strip().upper() if c_tier < len(r) and r[c_tier] else None) or None
        sp_name = (str(r[c_sp]).strip() if c_sp < len(r) and r[c_sp] else None) or None
        beat = (str(r[c_beat]).strip() if c_beat < len(r) and r[c_beat] else None) or None
        l3m = float(r[c_l3m]) if c_l3m < len(r) and isinstance(r[c_l3m], (int, float)) else None
        mtd_tgt = float(r[c_mtd_tgt]) if c_mtd_tgt < len(r) and isinstance(r[c_mtd_tgt], (int, float)) else None

        # Resolve salesperson
        sp_user_id = None
        if sp_name:
            key = sp_name.lower().split()[0]
            sp_user_id = name_to_user.get(key)
            if not sp_user_id:
                stats["salespersons_missing"].add(sp_name)

        # Match customer by normalised outlet name
        norm = _normalize(outlet)
        matched_ids = norm_idx.get(norm, [])

        if not matched_ids:
            # try contains-match (only one substring)
            for k in norm_idx:
                if (norm in k or k in norm) and abs(len(k) - len(norm)) <= 6:
                    matched_ids = norm_idx[k]
                    break

        if not matched_ids:
            # create stub customer (will be linked to Zoho later when seen)
            new_cust = {
                "id": new_id(),
                "name": outlet,
                "code": f"MAP-{abs(hash(outlet)) % 100000:05d}",
                "area": "Chandigarh",
                "city": "Chandigarh",
                "state": "Chandigarh",
                "contact_person": None,
                "phone": None,
                "email": None,
                "gstin": None,
                "credit_limit": 0.0,
                "brand_preferences": [],
                "assigned_to": sp_user_id,
                "lat": None,
                "lng": None,
                "outstanding": 0.0,
                "overdue": 0.0,
                "total_purchases": 0.0,
                "credit_risk_score": 50,
                "payment_behaviour_score": 50,
                "tier": tier,
                "beat_days": beat,
                "monthly_target": mtd_tgt,
                "l3m_avg_value": l3m,
                "created_at": now_iso(),
                "source": "mapping_only",
            }
            await db.customers.insert_one(new_cust)
            stats["customers_created"] += 1
            norm_idx.setdefault(norm, []).append(new_cust["id"])
            matched_ids = [new_cust["id"]]

        upd = {}
        if sp_user_id:
            upd["assigned_to"] = sp_user_id
        if tier:
            upd["tier"] = tier
            stats["tiers_set"][tier] = stats["tiers_set"].get(tier, 0) + 1
        if beat:
            upd["beat_days"] = beat
        if mtd_tgt is not None:
            upd["monthly_target"] = mtd_tgt
        if l3m is not None:
            upd["l3m_avg_value"] = l3m

        for cid in matched_ids:
            await db.customers.update_one({"id": cid}, {"$set": upd})
            stats["customers_assigned"] += 1

    stats["salespersons_missing"] = sorted(stats["salespersons_missing"])
    return stats
