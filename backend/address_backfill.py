"""Backfill customer addresses by fetching each Zoho contact's detail endpoint.

Run in background — uses concurrent batches to respect Zoho's rate limits (~100 req/min).
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


async def backfill_addresses(db, max_concurrent: int = 8, batch_delay: float = 1.0,
                              limit: Optional[int] = None) -> dict:
    """Fetch each Zoho customer's detail endpoint to populate full billing address."""
    from zoho_sync import get_token, REGIONS
    from address_utils import normalize_area, full_address, state_from_gstin

    started = datetime.now(timezone.utc)
    log_id = f"backfill-addr-{int(started.timestamp())}"
    log_doc = {"id": log_id, "started_at": started.isoformat(),
               "type": "address_backfill", "status": "running"}
    await db.sync_logs.insert_one(log_doc)

    token = await get_token(db)
    cfg = await db.config.find_one({"key": "zoho"}, {"_id": 0})
    if not token or not cfg:
        await db.sync_logs.update_one(
            {"id": log_id},
            {"$set": {"status": "failed", "message": "Zoho credentials missing",
                      "finished_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"ok": False, "error": "Zoho credentials missing"}

    _, api_base = REGIONS[cfg["region"]]
    org_id = cfg["organization_id"]
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}

    q = {"zoho_contact_id": {"$ne": None}, "$or": [
        {"area": "Mumbai"}, {"area": None}, {"area": "—"}, {"address": None}, {"address": ""},
    ]}
    customers = await db.customers.find(q, {"_id": 0, "id": 1, "zoho_contact_id": 1, "gstin": 1}).to_list(50000)
    if limit:
        customers = customers[:limit]
    total = len(customers)

    updated = 0
    failed = 0
    sem = asyncio.Semaphore(max_concurrent)

    async with httpx.AsyncClient(timeout=20.0) as client:
        async def fetch_one(c):
            nonlocal updated, failed
            async with sem:
                for attempt in range(4):
                    try:
                        r = await client.get(
                            f"{api_base}/books/v3/contacts/{c['zoho_contact_id']}",
                            headers=headers,
                            params={"organization_id": org_id},
                        )
                        if r.status_code == 429 or (r.status_code == 400 and "limit" in r.text.lower()):
                            # rate limited — back off and retry
                            wait = float(r.headers.get("Retry-After") or (2 ** attempt))
                            await asyncio.sleep(min(wait, 10))
                            continue
                        if r.status_code != 200:
                            failed += 1
                            return
                        d = r.json().get("contact", {})
                        ba = d.get("billing_address") or {}
                        if not ba:
                            return
                        addr_text = " ".join(filter(None, [
                            ba.get("attention") or "",
                            ba.get("address") or "",
                            ba.get("street2") or "",
                        ]))
                        area = normalize_area(
                            address=addr_text,
                            city=ba.get("city") or "",
                            attention=ba.get("attention") or "",
                        )
                        state = ba.get("state") or state_from_gstin(c.get("gstin") or "") or "—"
                        city = ba.get("city") or "—"
                        upd = {
                            "address": full_address(ba) or None,
                            "area": area,
                            "city": city,
                            "state": state,
                            "zip": ba.get("zip") or None,
                        }
                        await db.customers.update_one({"id": c["id"]}, {"$set": upd})
                        updated += 1
                        return
                    except Exception as e:
                        logger.debug("backfill failed for %s: %s", c.get("zoho_contact_id"), e)
                        await asyncio.sleep(1)
                failed += 1

        # Run in batches of size max_concurrent * 4 to allow batch_delay between waves
        batch_size = max(max_concurrent * 4, 32)
        for i in range(0, total, batch_size):
            chunk = customers[i:i + batch_size]
            await asyncio.gather(*(fetch_one(c) for c in chunk))
            if batch_delay and i + batch_size < total:
                await asyncio.sleep(batch_delay)

    finished = datetime.now(timezone.utc)
    result = {
        "id": log_id,
        "status": "completed",
        "total": total,
        "updated": updated,
        "failed": failed,
        "finished_at": finished.isoformat(),
        "duration_seconds": round((finished - started).total_seconds(), 1),
    }
    await db.sync_logs.update_one({"id": log_id}, {"$set": result})
    return result
