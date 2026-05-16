"""Scheme management: Excel/CSV upload, Zoho brand sync, progress recomputation, leaderboard."""
from datetime import datetime, timezone
from typing import Optional
import io
import csv
import os
import logging

import httpx
import pandas as pd

from models import new_id, now_iso

logger = logging.getLogger(__name__)


REQUIRED_COLS = {"name", "brand", "start_date", "end_date"}
OPTIONAL_COLS = {"type", "description", "target_amount", "reward", "active"}


def _norm_date(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    # Try pandas to_datetime
    try:
        return pd.to_datetime(s).strftime("%Y-%m-%d")
    except Exception:
        return s[:10]


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
    # Normalise keys lowercase
    out = []
    for r in rows:
        clean = {str(k).strip().lower(): v for k, v in r.items()}
        out.append(clean)
    return out


async def upload_schemes_from_file(db, file_bytes: bytes, filename: str) -> dict:
    """Parse uploaded Excel/CSV and upsert schemes. Returns counts."""
    rows = _parse_rows(file_bytes, filename)
    if not rows:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": ["empty file"]}

    # Validate first row columns
    first = rows[0]
    missing = REQUIRED_COLS - set(first.keys())
    if missing:
        return {"created": 0, "updated": 0, "skipped": 0,
                "errors": [f"Missing required columns: {sorted(missing)}. Required: {sorted(REQUIRED_COLS)}"]}

    created = updated = skipped = 0
    errors: list[str] = []
    for i, row in enumerate(rows, start=2):
        try:
            name = (str(row.get("name") or "")).strip()
            brand = (str(row.get("brand") or "")).strip()
            if not name or not brand:
                skipped += 1
                continue
            doc = {
                "name": name,
                "brand": brand,
                "type": (str(row.get("type") or "value")).strip().lower() or "value",
                "description": (str(row.get("description") or "")).strip(),
                "start_date": _norm_date(row.get("start_date")),
                "end_date": _norm_date(row.get("end_date")),
                "target_amount": float(row.get("target_amount") or 0) if str(row.get("target_amount") or "").strip() else 0.0,
                "reward": (str(row.get("reward") or "")).strip(),
                "active": str(row.get("active", "true")).strip().lower() not in ("false", "0", "no", "n"),
            }
            existing = await db.schemes.find_one(
                {"name": doc["name"], "brand": doc["brand"], "start_date": doc["start_date"]},
                {"_id": 0, "id": 1},
            )
            if existing:
                await db.schemes.update_one({"id": existing["id"]}, {"$set": doc})
                updated += 1
            else:
                doc["id"] = new_id()
                doc["progress"] = 0.0
                doc["created_at"] = now_iso()
                await db.schemes.insert_one(doc)
                created += 1
        except Exception as e:
            errors.append(f"Row {i}: {e}")
            skipped += 1
    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors[:20]}


# ============ ZOHO BRAND SYNC ============
ZOHO_ITEMS_PATH = "/books/v3/items"


async def sync_zoho_brands(db) -> dict:
    """Pull items from Zoho Books and extract unique brands. Stores them in a 'brands' collection
    so the UI can offer a brand dropdown for scheme creation. Best-effort: requires Zoho creds.
    """
    try:
        from zoho_sync import _credentials_present, get_token, detect_region_and_org, REGIONS, _token_cache
    except Exception as e:
        return {"ok": False, "error": f"Zoho module not available: {e}"}

    if not _credentials_present():
        return {"ok": False, "error": "Zoho credentials not configured"}

    token = await get_token(db)
    if not token:
        return {"ok": False, "error": "Zoho auth failed (refresh token invalid?)"}

    cfg = await db.config.find_one({"key": "zoho"}, {"_id": 0}) or {}
    region = cfg.get("region") or _token_cache.get("region") or os.environ.get("ZOHO_REGION") or ".in"
    org_id = cfg.get("organization_id") or os.environ.get("ZOHO_ORGANIZATION_ID")
    if not org_id:
        det = await detect_region_and_org(db)
        if det.get("ok"):
            org_id = det.get("organization_id")
            region = det.get("region", region)
    if not org_id:
        return {"ok": False, "error": "Zoho organization_id unknown"}

    _, api_base = REGIONS.get(region, REGIONS[".in"])
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    brands: set[str] = set()
    page = 1
    pulled = 0
    async with httpx.AsyncClient(timeout=30) as http:
        while True:
            r = await http.get(
                f"{api_base}{ZOHO_ITEMS_PATH}",
                headers=headers,
                params={"organization_id": org_id, "page": page, "per_page": 200},
            )
            if r.status_code != 200:
                return {"ok": False, "error": f"Zoho items API HTTP {r.status_code}: {r.text[:200]}"}
            data = r.json()
            items = data.get("items", [])
            pulled += len(items)
            for it in items:
                b = (it.get("brand") or "").strip()
                if b:
                    brands.add(b)
                cf = it.get("custom_fields", []) or []
                for f in cf:
                    if (f.get("label") or "").lower() in ("brand", "manufacturer") and f.get("value"):
                        brands.add(str(f["value"]).strip())
            ctx = data.get("page_context", {})
            if not ctx.get("has_more_page"):
                break
            page += 1
            if page > 50:
                break

    # Persist
    out_brands = sorted({b for b in brands if b})
    await db.brands.update_one(
        {"id": "zoho-brands"},
        {"$set": {
            "id": "zoho-brands",
            "source": "zoho",
            "brands": out_brands,
            "items_pulled": pulled,
            "synced_at": now_iso(),
        }},
        upsert=True,
    )
    return {"ok": True, "items_pulled": pulled, "brand_count": len(out_brands), "brands": out_brands}


# ============ PROGRESS / LEADERBOARD ============
async def recompute_scheme_progress(db, scheme_id: str) -> dict:
    """Recompute progress for a single scheme based on invoices in [start_date, end_date]
    matching the scheme's brand. Returns updated scheme doc + leaderboard."""
    s = await db.schemes.find_one({"id": scheme_id}, {"_id": 0})
    if not s:
        return {"error": "not found"}

    start = (s.get("start_date") or "")[:10]
    end = (s.get("end_date") or "")[:10]
    brand_raw = (s.get("brand") or "").strip()
    brand = brand_raw.lower()
    target = float(s.get("target_amount") or 0)

    # Use date range — invoices store ISO date strings ("date" field in this codebase).
    # We do start-of-day → end-of-day inclusive.
    invoices = await db.invoices.find(
        {"date": {"$gte": start, "$lte": end + "T23:59:59"}},
        {"_id": 0},
    ).to_list(50000)

    by_customer: dict[str, float] = {}
    total = 0.0
    for inv in invoices:
        amt = 0.0
        # 1. Invoice-level brand tag (existing schema uses 'brand')
        inv_brand = (str(inv.get("brand") or "")).lower()
        if brand and inv_brand and brand in inv_brand:
            amt = float(inv.get("amount") or inv.get("total") or 0)
        else:
            # 2. Line-item / items brand match
            line_items = inv.get("line_items") or inv.get("items") or []
            line_total = 0.0
            if isinstance(line_items, list):
                for li in line_items:
                    if not isinstance(li, dict):
                        continue
                    li_brand = (str(li.get("brand") or li.get("item_name") or li.get("name") or "")).lower()
                    if brand and brand in li_brand:
                        line_total += float(li.get("total") or li.get("item_total") or li.get("amount") or 0)
            if line_total > 0:
                amt = line_total
            elif not brand:
                amt = float(inv.get("amount") or inv.get("total") or 0)
        if amt <= 0:
            continue
        cust = inv.get("customer_id") or inv.get("zoho_customer_id") or "unknown"
        by_customer[cust] = by_customer.get(cust, 0) + amt
        total += amt

    progress = min(100.0, round((total / target) * 100, 2)) if target > 0 else 0.0
    await db.schemes.update_one(
        {"id": scheme_id},
        {"$set": {"progress": progress, "achieved_amount": round(total, 2),
                  "last_computed_at": now_iso()}},
    )

    # Leaderboard top 50
    top = sorted(by_customer.items(), key=lambda x: -x[1])[:50]
    customer_ids = [cid for cid, _ in top]
    cmap = {}
    if customer_ids:
        cursor = db.customers.find({"id": {"$in": customer_ids}}, {"_id": 0, "id": 1, "name": 1, "tier": 1})
        async for c in cursor:
            cmap[c["id"]] = c
    leaderboard = [
        {"customer_id": cid, "name": cmap.get(cid, {}).get("name", cid),
         "tier": cmap.get(cid, {}).get("tier"), "amount": round(amt, 2),
         "pct_of_target": round((amt / target) * 100, 1) if target > 0 else 0.0}
        for cid, amt in top
    ]

    s["progress"] = progress
    s["achieved_amount"] = round(total, 2)
    return {"scheme": s, "leaderboard": leaderboard, "total": round(total, 2)}


async def recompute_all_schemes(db) -> dict:
    schemes = await db.schemes.find({"active": True}, {"_id": 0, "id": 1}).to_list(500)
    updated = 0
    for s in schemes:
        try:
            await recompute_scheme_progress(db, s["id"])
            updated += 1
        except Exception as e:
            logger.warning(f"scheme recompute failed for {s['id']}: {e}")
    return {"updated": updated}
