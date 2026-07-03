"""Background scheduler.

Two independent jobs:
  * local_aggregate_job — hourly, recomputes customer outstanding/overdue from LOCAL
    data. Zero Zoho API calls. Keeps the dashboard fresh between daily Zoho pulls.
  * zoho_daily_job — once a day (ZOHO_SYNC_HOUR, default 02:00 IST). Incremental:
    pulls only records changed since the last successful sync. Disable with
    ZOHO_AUTOSYNC_ENABLED=false.
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


# Guards against a slow sync overlapping the next scheduled run.
_zoho_sync_running = False


def start_scheduler(db):
    global scheduler
    if scheduler:
        return scheduler
    import os
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    def _truthy(v: str | None, default: bool) -> bool:
        if v is None:
            return default
        return v.strip().lower() in {"1", "true", "yes", "on"}

    autosync_enabled = _truthy(os.environ.get("ZOHO_AUTOSYNC_ENABLED"), True)
    try:
        sync_hour = int(os.environ.get("ZOHO_SYNC_HOUR", "2"))  # 2 AM IST by default
    except ValueError:
        sync_hour = 2

    async def local_aggregate_job():
        """Hourly — recompute customer outstanding/overdue from LOCAL data only.
        Makes ZERO Zoho API calls; keeps the dashboard fresh between daily Zoho pulls."""
        try:
            await refresh_customer_aggregates(db)
        except Exception as e:
            logger.exception("Local aggregate refresh failed: %s", e)

    async def zoho_daily_job():
        """Once per day — incremental Zoho sync: only records changed since the last
        successful run (checkpoint), falling back to the last 24h on first run."""
        global _zoho_sync_running
        if _zoho_sync_running:
            logger.info("Zoho daily sync skipped — a sync is already running")
            return
        zoho_ready = bool(
            os.environ.get("ZOHO_CLIENT_ID")
            and os.environ.get("ZOHO_CLIENT_SECRET")
            and os.environ.get("ZOHO_REFRESH_TOKEN")
        )
        if not zoho_ready:
            return
        cfg = await db.config.find_one({"key": "zoho"}, {"_id": 0})
        if not (cfg and cfg.get("region") and cfg.get("organization_id")):
            return
        _zoho_sync_running = True
        try:
            from zoho_sync import sync_zoho
            result = await sync_zoho(db, use_checkpoint=True)
            logger.info("Zoho daily sync: %s", result.get("message", result.get("status")))
        except Exception as e:
            logger.exception("Zoho daily sync failed: %s", e)
        finally:
            _zoho_sync_running = False

    # Local aggregates: hourly, no Zoho calls.
    scheduler.add_job(local_aggregate_job, "interval", hours=1, id="refresh_aggregates")

    # Zoho: once a day at ZOHO_SYNC_HOUR (IST), incremental only.
    if autosync_enabled:
        scheduler.add_job(zoho_daily_job, "cron", hour=sync_hour, minute=0, id="zoho_daily_sync")
        logger.info(
            "Scheduler started — hourly local aggregates + daily incremental Zoho sync at %02d:00 IST",
            sync_hour,
        )
    else:
        logger.info("Scheduler started — hourly local aggregates; Zoho auto-sync DISABLED (ZOHO_AUTOSYNC_ENABLED=false)")

    scheduler.start()
    return scheduler


def stop_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
