"""Zoho Books sync engine.

Auto-detects region (.in, .com, .eu, .com.au, .jp) and organization id.
Refreshes access token using refresh_token grant.
Pulls customers, invoices, payments, credit notes from Zoho Books and stores in MongoDB,
preserving local fields (assigned_to, lat/lng, brand_preferences).
"""
import os
import logging
import time
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

REGIONS = {
    ".in": ("https://accounts.zoho.in", "https://www.zohoapis.in"),
    ".com": ("https://accounts.zoho.com", "https://www.zohoapis.com"),
    ".eu": ("https://accounts.zoho.eu", "https://www.zohoapis.eu"),
    ".com.au": ("https://accounts.zoho.com.au", "https://www.zohoapis.com.au"),
    ".jp": ("https://accounts.zoho.jp", "https://www.zohoapis.jp"),
}

# Cached access token
_token_cache = {"token": None, "expires_at": 0, "region": None}


def _credentials_present() -> bool:
    return bool(os.environ.get("ZOHO_CLIENT_ID") and os.environ.get("ZOHO_CLIENT_SECRET") and os.environ.get("ZOHO_REFRESH_TOKEN"))


async def _fetch_token(region_key: str) -> Optional[dict]:
    accounts_url, _ = REGIONS[region_key]
    data = {
        "refresh_token": os.environ["ZOHO_REFRESH_TOKEN"],
        "client_id": os.environ["ZOHO_CLIENT_ID"],
        "client_secret": os.environ["ZOHO_CLIENT_SECRET"],
        "grant_type": "refresh_token",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.post(f"{accounts_url}/oauth/v2/token", data=data)
        if r.status_code == 200:
            j = r.json()
            if j.get("access_token"):
                return j
        return None
    except Exception as e:
        logger.debug("Token fetch failed for region %s: %s", region_key, e)
        return None


async def detect_region_and_org(db) -> dict:
    """Probe each region with the refresh token; on success, hit /organizations to capture org id."""
    if not _credentials_present():
        return {"ok": False, "error": "Zoho credentials not set in .env"}

    cfg_region = os.environ.get("ZOHO_REGION") or None
    candidates = [cfg_region] if cfg_region else list(REGIONS.keys())

    for r in candidates:
        if r not in REGIONS:
            continue
        tok = await _fetch_token(r)
        if not tok:
            continue
        access = tok["access_token"]
        _, api_url = REGIONS[r]
        try:
            async with httpx.AsyncClient(timeout=20.0) as c:
                resp = await c.get(
                    f"{api_url}/books/v3/organizations",
                    headers={"Authorization": f"Zoho-oauthtoken {access}"},
                )
            if resp.status_code != 200:
                continue
            orgs = resp.json().get("organizations", [])
            if not orgs:
                continue
            # Prefer one matching ZOHO_ORGANIZATION_ID, else first
            target = None
            wanted = os.environ.get("ZOHO_ORGANIZATION_ID")
            if wanted:
                target = next((o for o in orgs if str(o.get("organization_id")) == str(wanted)), None)
            target = target or orgs[0]
            org_id = str(target.get("organization_id"))
            org_name = target.get("name")

            _token_cache.update({
                "token": access,
                "expires_at": time.time() + int(tok.get("expires_in", 3600)) - 60,
                "region": r,
            })

            await db.config.update_one(
                {"key": "zoho"},
                {"$set": {
                    "key": "zoho",
                    "region": r,
                    "organization_id": org_id,
                    "organization_name": org_name,
                    "organizations": [{"id": str(o.get("organization_id")), "name": o.get("name")} for o in orgs],
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True,
            )
            return {"ok": True, "region": r, "organization_id": org_id, "organization_name": org_name, "all_orgs": orgs}
        except Exception as e:
            logger.exception("Org probe failed for region %s: %s", r, e)
            continue
    return {"ok": False, "error": "Could not authenticate with any Zoho region. Check Client ID / Secret / Refresh Token scope (ZohoBooks.fullaccess.all)."}


async def get_token(db) -> Optional[str]:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]
    cfg = await db.config.find_one({"key": "zoho"}, {"_id": 0}) or {}
    region = cfg.get("region") or os.environ.get("ZOHO_REGION") or None
    if not region:
        detect = await detect_region_and_org(db)
        if not detect["ok"]:
            return None
        return _token_cache["token"]
    tok = await _fetch_token(region)
    if not tok:
        return None
    _token_cache.update({
        "token": tok["access_token"],
        "expires_at": time.time() + int(tok.get("expires_in", 3600)) - 60,
        "region": region,
    })
    return tok["access_token"]


async def _get_paginated(client: httpx.AsyncClient, url: str, headers: dict, params: dict, key: str, max_pages: int = 50):
    out = []
    page = 1
    while page <= max_pages:
        p = {**params, "page": page, "per_page": 200}
        r = await client.get(url, headers=headers, params=p)
        if r.status_code != 200:
            logger.warning("Zoho %s page %d failed: %s %s", url, page, r.status_code, r.text[:200])
            break
        data = r.json()
        items = data.get(key, [])
        out.extend(items)
        pc = data.get("page_context", {})
        if not pc.get("has_more_page"):
            break
        page += 1
    return out


async def _sync_salespersons(db, client: httpx.AsyncClient, api_base: str, headers: dict, org_id: str) -> dict:
    """Pull Zoho salespersons → ensure local user accounts → return map zoho_sp_id → local_user_id."""
    from auth import hash_password
    from models import new_id, now_iso
    r = await client.get(f"{api_base}/books/v3/salespersons", headers=headers, params={"organization_id": org_id})
    if r.status_code != 200:
        logger.warning("Failed to fetch salespersons: %s", r.text[:200])
        return {}
    payload = r.json()
    raw = payload.get("data") or payload.get("salespersons") or []
    mapping = {}
    EXCLUDE_NAMES = {"admin", "ne office", "office"}
    for sp in raw:
        if not sp.get("is_active", True):
            continue
        sp_id = str(sp.get("salesperson_id"))
        name = (sp.get("salesperson_name") or "").strip()
        email = (sp.get("salesperson_email") or "").strip().lower()
        if name.lower() in EXCLUDE_NAMES:
            continue
        local = await db.users.find_one({"zoho_salesperson_id": sp_id}, {"_id": 0})
        if not local and email:
            local = await db.users.find_one({"email": email}, {"_id": 0})
        if not local and name:
            slug = name.lower().split()[0]
            local = await db.users.find_one({"email": f"{slug}@nalanda.com"}, {"_id": 0})
        if not local:
            slug = name.lower().split()[0] if name else f"sp{sp_id[-4:]}"
            user_email = email or f"{slug}@nalanda.com"
            existing = await db.users.find_one({"email": user_email})
            if existing:
                local = existing
            else:
                doc = {
                    "id": new_id(),
                    "email": user_email,
                    "password_hash": hash_password("Sales@123"),
                    "name": name or slug.title(),
                    "role": "sales",
                    "phone": sp.get("salesperson_mobile") or "",
                    "territory": f"{name} Beat",
                    "active": True,
                    "zoho_salesperson_id": sp_id,
                    "zoho_salesperson_email": email,
                    "created_at": now_iso(),
                }
                await db.users.insert_one(doc)
                local = doc
        if not local.get("zoho_salesperson_id"):
            await db.users.update_one({"id": local["id"]}, {"$set": {"zoho_salesperson_id": sp_id, "zoho_salesperson_email": email}})
        mapping[sp_id] = local["id"]
    return mapping



async def sync_zoho(db, modified_since_hours: Optional[int] = None) -> dict:
    """Pull customers, invoices, payments, credit_notes from Zoho Books → MongoDB.

    Preserves local fields on customers (assigned_to, lat, lng, brand_preferences, area).
    Idempotent: matches on Zoho id stored as zoho_contact_id / zoho_invoice_id / zoho_payment_id.
    """
    started = datetime.now(timezone.utc)
    log_id = f"zoho-{int(started.timestamp())}"

    if not _credentials_present():
        log = {"id": log_id, "started_at": started.isoformat(), "status": "skipped",
               "type": "zoho_sync", "message": "Zoho credentials missing in .env"}
        await db.sync_logs.insert_one(log)
        log.pop("_id", None)
        return log

    cfg = await db.config.find_one({"key": "zoho"}, {"_id": 0})
    if not cfg or not cfg.get("region") or not cfg.get("organization_id"):
        detect = await detect_region_and_org(db)
        if not detect["ok"]:
            log = {"id": log_id, "started_at": started.isoformat(), "status": "failed",
                   "type": "zoho_sync", "message": detect.get("error", "Region detection failed")}
            await db.sync_logs.insert_one(log)
            log.pop("_id", None)
            return log
        cfg = await db.config.find_one({"key": "zoho"}, {"_id": 0})

    region = cfg["region"]
    org_id = cfg["organization_id"]
    _, api_base = REGIONS[region]

    token = await get_token(db)
    if not token:
        log = {"id": log_id, "started_at": started.isoformat(), "status": "failed",
               "type": "zoho_sync", "message": "Failed to obtain access token"}
        await db.sync_logs.insert_one(log)
        log.pop("_id", None)
        return log

    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    params = {"organization_id": org_id}
    if modified_since_hours:
        since = (started - timedelta(hours=modified_since_hours)).strftime("%Y-%m-%dT%H:%M:%S%z")
        params["last_modified_time"] = since

    counts = {"customers": 0, "invoices": 0, "payments": 0, "credit_notes": 0, "errors": 0}

    try:
        async with httpx.AsyncClient(timeout=60.0) as c:
            # ---------- SALESPERSONS (must come first so customer.assigned_to can be set) ----------
            sp_map = await _sync_salespersons(db, c, api_base, headers, org_id)
            counts["salespersons"] = len(sp_map)

            # ---------- CUSTOMERS (contacts where contact_type=customer) ----------
            from address_utils import normalize_area, full_address, state_from_gstin
            contacts = await _get_paginated(c, f"{api_base}/books/v3/contacts", headers,
                                             {**params, "contact_type": "customer"}, "contacts")
            for ct in contacts:
                zid = str(ct.get("contact_id"))
                existing = await db.customers.find_one({"zoho_contact_id": zid}, {"_id": 0})
                ba = ct.get("billing_address") or {}
                addr_str = full_address(ba)
                gstin = ct.get("gst_no") or (existing or {}).get("gstin") or ""
                area = normalize_area(
                    address=" ".join([ba.get("address") or "", ba.get("street2") or "", ba.get("attention") or ""]),
                    city=ba.get("city") or "",
                    attention=ba.get("attention") or "",
                )
                state = ba.get("state") or state_from_gstin(gstin) or "—"
                city = ba.get("city") or area
                doc = {
                    "zoho_contact_id": zid,
                    "name": ct.get("contact_name") or ct.get("company_name") or "Unknown",
                    "code": ct.get("cf_code") or (existing or {}).get("code") or f"ZOHO-{zid[-6:]}",
                    "phone": ct.get("phone") or ct.get("mobile") or (existing or {}).get("phone"),
                    "email": ct.get("email") or (existing or {}).get("email"),
                    "gstin": gstin or None,
                    "credit_limit": float(ct.get("credit_limit") or (existing or {}).get("credit_limit") or 0),
                    "outstanding": float(ct.get("outstanding_receivable_amount") or 0),
                    "address": addr_str or (existing or {}).get("address"),
                    "area": area if area != "—" else (existing or {}).get("area") or "—",
                    "city": city or (existing or {}).get("city") or "—",
                    "state": state if state != "—" else (existing or {}).get("state") or "—",
                    "zip": ba.get("zip") or (existing or {}).get("zip"),
                    "last_synced_at": started.isoformat(),
                }
                if existing:
                    await db.customers.update_one({"zoho_contact_id": zid}, {"$set": doc})
                else:
                    from models import new_id, now_iso
                    doc.update({
                        "id": new_id(),
                        "contact_person": ct.get("contact_name"),
                        "brand_preferences": [],
                        "assigned_to": None,
                        "lat": None, "lng": None,
                        "overdue": 0.0,
                        "total_purchases": 0.0,
                        "credit_risk_score": 50,
                        "payment_behaviour_score": 50,
                        "created_at": now_iso(),
                    })
                    await db.customers.insert_one(doc)
                counts["customers"] += 1

            # build map customer_zoho_id → local id
            local = await db.customers.find({"zoho_contact_id": {"$ne": None}}, {"_id": 0, "id": 1, "zoho_contact_id": 1}).to_list(20000)
            zid_to_local = {c["zoho_contact_id"]: c["id"] for c in local}

            # ---------- INVOICES ----------
            invoices = await _get_paginated(c, f"{api_base}/books/v3/invoices", headers, params, "invoices")
            for inv in invoices:
                zid = str(inv.get("invoice_id"))
                local_cid = zid_to_local.get(str(inv.get("customer_id")))
                doc = {
                    "zoho_invoice_id": zid,
                    "invoice_no": inv.get("invoice_number"),
                    "customer_id": local_cid,
                    "date": inv.get("date"),
                    "due_date": inv.get("due_date"),
                    "amount": float(inv.get("total") or 0),
                    "paid_amount": float(inv.get("total") or 0) - float(inv.get("balance") or 0),
                    "status": (inv.get("status") or "unpaid").lower(),
                    "brand": (inv.get("line_items") or [{}])[0].get("name", "Other").split()[0],
                    "items": [{
                        "sku": li.get("item_id"),
                        "product": li.get("name", ""),
                        "brand": li.get("name", "").split()[0] if li.get("name") else "Other",
                        "qty": int(li.get("quantity") or 0),
                        "unit_price": float(li.get("rate") or 0),
                        "amount": float(li.get("item_total") or 0),
                    } for li in inv.get("line_items", [])],
                    "last_synced_at": started.isoformat(),
                    "zoho_salesperson_id": str(inv.get("salesperson_id") or ""),
                    "salesperson_id": sp_map.get(str(inv.get("salesperson_id") or "")),
                    "salesperson_name": inv.get("salesperson_name"),
                }
                await db.invoices.update_one(
                    {"zoho_invoice_id": zid},
                    {"$set": doc, "$setOnInsert": {"id": _new_id(), "created_at": started.isoformat()}},
                    upsert=True,
                )
                counts["invoices"] += 1

                # Assign customer to the salesperson seen on this invoice (most-recent invoice wins)
                local_uid = sp_map.get(str(inv.get("salesperson_id") or ""))
                if local_cid and local_uid:
                    await db.customers.update_one({"id": local_cid}, {"$set": {"assigned_to": local_uid}})

            # ---------- PAYMENTS ----------
            payments = await _get_paginated(c, f"{api_base}/books/v3/customerpayments", headers, params, "customerpayments")
            for p in payments:
                zid = str(p.get("payment_id"))
                doc = {
                    "zoho_payment_id": zid,
                    "customer_id": zid_to_local.get(str(p.get("customer_id"))),
                    "amount": float(p.get("amount") or 0),
                    "date": p.get("date"),
                    "method": (p.get("payment_mode") or "neft").lower(),
                    "reference": p.get("reference_number"),
                    "notes": p.get("description"),
                    "last_synced_at": started.isoformat(),
                }
                await db.payments.update_one(
                    {"zoho_payment_id": zid},
                    {"$set": doc, "$setOnInsert": {"id": _new_id(), "created_at": started.isoformat()}},
                    upsert=True,
                )
                counts["payments"] += 1

            # ---------- CREDIT NOTES ----------
            credit_notes = await _get_paginated(c, f"{api_base}/books/v3/creditnotes", headers, params, "creditnotes")
            for cn in credit_notes:
                zid = str(cn.get("creditnote_id"))
                doc = {
                    "zoho_credit_note_id": zid,
                    "customer_id": zid_to_local.get(str(cn.get("customer_id"))),
                    "credit_note_no": cn.get("creditnote_number"),
                    "date": cn.get("date"),
                    "amount": float(cn.get("total") or 0),
                    "balance": float(cn.get("balance") or 0),
                    "status": (cn.get("status") or "open").lower(),
                    "last_synced_at": started.isoformat(),
                }
                await db.credit_notes.update_one(
                    {"zoho_credit_note_id": zid},
                    {"$set": doc, "$setOnInsert": {"id": _new_id(), "created_at": started.isoformat()}},
                    upsert=True,
                )
                counts["credit_notes"] += 1

    except Exception as e:
        logger.exception("Zoho sync failed: %s", e)
        log = {"id": log_id, "started_at": started.isoformat(),
               "status": "failed", "type": "zoho_sync",
               "synced": counts, "message": str(e)[:500]}
        await db.sync_logs.insert_one(log)
        log.pop("_id", None)
        return log

    # Recompute aggregates
    try:
        from scheduler import refresh_customer_aggregates
        await refresh_customer_aggregates(db)
    except Exception:
        pass

    log = {
        "id": log_id,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "type": "zoho_sync",
        "region": region,
        "organization_id": org_id,
        "synced": counts,
        "message": f"Synced {counts['customers']} customers, {counts['invoices']} invoices, {counts['payments']} payments, {counts['credit_notes']} credit notes.",
    }
    await db.sync_logs.insert_one(log)
    log.pop("_id", None)
    return log


def _new_id():
    from models import new_id
    return new_id()
