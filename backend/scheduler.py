"""Background scheduler — refreshes customer aggregates every hour (live-feel even before Zoho).

Once Zoho credentials are added, the same job slot will trigger zoho_sync.fetch().
"""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler | None = None


async def refresh_customer_aggregates(db):
    """Recalculate customer outstanding/overdue/totals from current invoices+payments."""
    now = datetime.now(timezone.utc)
    customers = await db.customers.find({}, {"_id": 0, "id": 1}).to_list(5000)
    for c in customers:
        invs = await db.invoices.find({"customer_id": c["id"]}, {"_id": 0}).to_list(2000)
        pays = await db.payments.find({"customer_id": c["id"]}, {"_id": 0}).to_list(2000)
        # Recompute overdue status on invoices
        for inv in invs:
            try:
                due_dt = datetime.fromisoformat(inv["due_date"])
            except Exception:
                continue
            paid = inv.get("paid_amount", 0)
            amount = inv.get("amount", 0)
            new_status = inv.get("status", "unpaid")
            if paid >= amount - 0.01:
                new_status = "paid"
            elif (now - due_dt).days > 0 and paid < amount:
                new_status = "overdue"
            elif paid > 0 and paid < amount:
                new_status = "partial"
            else:
                new_status = "unpaid"
            if new_status != inv.get("status"):
                await db.invoices.update_one({"id": inv["id"]}, {"$set": {"status": new_status}})
                inv["status"] = new_status

        total_purchases = sum(i.get("amount", 0) for i in invs)
        outstanding = sum(i.get("amount", 0) - i.get("paid_amount", 0) for i in invs if i.get("status") != "paid")
        overdue = sum(i.get("amount", 0) - i.get("paid_amount", 0) for i in invs if i.get("status") == "overdue")
        last_payment = max((p.get("date", "") for p in pays), default=None)
        last_order = max((i.get("date", "") for i in invs), default=None)
        await db.customers.update_one(
            {"id": c["id"]},
            {"$set": {
                "total_purchases": total_purchases,
                "outstanding": outstanding,
                "overdue": overdue,
                "last_payment_date": last_payment,
                "last_order_date": last_order,
            }}
        )
    await db.sync_logs.insert_one({
        "id": f"agg-{int(now.timestamp())}",
        "started_at": now.isoformat(),
        "status": "completed",
        "type": "aggregate_refresh",
        "synced": {"customers": len(customers)},
        "message": "Hourly customer aggregate refresh from local invoices/payments. Zoho sync will replace this once credentials are configured.",
    })
    logger.info("Aggregates refreshed for %d customers", len(customers))


def start_scheduler(db):
    global scheduler
    if scheduler:
        return scheduler
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    async def hourly_job():
        # If Zoho is configured, run a Zoho sync; otherwise refresh local aggregates
        try:
            import os
            zoho_ready = bool(os.environ.get("ZOHO_CLIENT_ID") and os.environ.get("ZOHO_CLIENT_SECRET") and os.environ.get("ZOHO_REFRESH_TOKEN"))
            if zoho_ready:
                from zoho_sync import sync_zoho
                cfg = await db.config.find_one({"key": "zoho"}, {"_id": 0})
                if cfg and cfg.get("region") and cfg.get("organization_id"):
                    await sync_zoho(db, modified_since_hours=2)
                    return
            await refresh_customer_aggregates(db)
        except Exception as e:
            logger.exception("Scheduled job failed: %s", e)

    # Every 30 minutes — pulls live Zoho data or refreshes aggregates
    scheduler.add_job(hourly_job, "interval", minutes=30, id="refresh_aggregates", next_run_time=None)
    scheduler.start()
    logger.info("Scheduler started — 30-min sync (Zoho if configured, else local aggregates)")
    return scheduler


def stop_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
