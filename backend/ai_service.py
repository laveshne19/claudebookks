"""AI service using Emergent LLM Key (Claude Sonnet 4.5) for customer intelligence."""
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


def _build_customer_brief(customer: dict, invoices: list, payments: list) -> str:
    """Compose a compact prompt-friendly brief of customer data."""
    recent_invoices = sorted(invoices, key=lambda x: x.get("date", ""), reverse=True)[:8]
    recent_payments = sorted(payments, key=lambda x: x.get("date", ""), reverse=True)[:5]

    brand_buys = {}
    product_buys = {}
    for inv in invoices:
        for item in inv.get("items", []):
            brand_buys[item["brand"]] = brand_buys.get(item["brand"], 0) + item["amount"]
            key = f"{item['brand']} {item['product']}"
            product_buys[key] = product_buys.get(key, 0) + item["qty"]

    top_brands = sorted(brand_buys.items(), key=lambda x: -x[1])[:3]
    top_products = sorted(product_buys.items(), key=lambda x: -x[1])[:5]

    brief = {
        "customer_name": customer["name"],
        "area": customer.get("area"),
        "tier": customer.get("tier"),
        "beat_days": customer.get("beat_days"),
        "monthly_target_inr": customer.get("monthly_target"),
        "l3m_avg_value_inr": customer.get("l3m_avg_value"),
        "credit_limit": customer.get("credit_limit"),
        "current_outstanding": customer.get("outstanding"),
        "current_overdue": customer.get("overdue"),
        "total_lifetime_purchases": customer.get("total_purchases"),
        "last_payment_date": customer.get("last_payment_date"),
        "last_order_date": customer.get("last_order_date"),
        "brand_preferences": customer.get("brand_preferences"),
        "top_brands_by_value": top_brands,
        "top_products_bought": top_products,
        "recent_invoices_count": len(recent_invoices),
        "recent_invoices_sample": [
            {"no": i.get("invoice_no"), "amount": i.get("amount"), "status": i.get("status"), "date": i.get("date")[:10]}
            for i in recent_invoices[:5]
        ],
        "recent_payments_sample": [
            {"amount": p.get("amount"), "date": p.get("date")[:10], "method": p.get("method")}
            for p in recent_payments
        ],
    }
    return json.dumps(brief, default=str, indent=2)


async def generate_customer_insights(customer: dict, invoices: list, payments: list) -> dict:
    """Generate AI-powered customer insights using Claude Sonnet 4.5."""
    brief = _build_customer_brief(customer, invoices, payments)
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return _fallback_insights(customer)

    system_message = (
        "You are a senior B2B sales analyst for Nalanda Enterprises, an Indian electronics & gadget distributor "
        "(Boat, Fireboltt, Noise, Logitech, Amazon, Swiss Military, Mivi). "
        "Generate concise, actionable customer intelligence for the salesperson visiting this dealer. "
        "Always respond with VALID JSON only — no markdown, no prose outside JSON. "
        "Scores are integers 0-100 where higher is better (lower credit risk = higher score)."
    )

    user_prompt = f"""Customer Data:
{brief}

Generate JSON with EXACTLY these keys:
{{
  "summary": "<2-3 sentence executive summary>",
  "predicted_next_order": "<best guess: timeframe + likely brand/product + estimated value in INR>",
  "credit_risk_score": <0-100 integer>,
  "payment_behaviour_score": <0-100 integer>,
  "recovery_approach": "<1-2 sentence concrete recovery suggestion>",
  "upsell_suggestions": ["<product 1>", "<product 2>", "<product 3>"],
  "pitch_points": ["<sales pitch 1>", "<pitch 2>", "<pitch 3>"],
  "best_visit_time": "<day of week + time-of-day suggestion based on patterns>"
}}"""

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"insights-{customer['id']}-{datetime.now(timezone.utc).strftime('%Y%m%d%H')}",
            system_message=system_message,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")

        response = await chat.send_message(UserMessage(text=user_prompt))
        text = response.strip()
        # strip code fences if any
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip("` \n")
        data = json.loads(text)
        data["customer_id"] = customer["id"]
        data["generated_at"] = datetime.now(timezone.utc).isoformat()
        # sanitize
        for k in ("credit_risk_score", "payment_behaviour_score"):
            data[k] = max(0, min(100, int(data.get(k, 50))))
        for k in ("upsell_suggestions", "pitch_points"):
            if not isinstance(data.get(k), list):
                data[k] = []
        return data
    except Exception as e:
        logger.exception("AI insight generation failed: %s", e)
        return _fallback_insights(customer)


def _fallback_insights(customer: dict) -> dict:
    """Deterministic fallback when LLM fails."""
    risk = int(customer.get("credit_risk_score", 50))
    pay = int(customer.get("payment_behaviour_score", 50))
    outstanding = customer.get("outstanding", 0)
    return {
        "customer_id": customer["id"],
        "summary": f"{customer['name']} is an established dealer in {customer.get('area', 'N/A')} with ₹{outstanding:,.0f} outstanding. Engagement priority depends on payment behaviour.",
        "predicted_next_order": "Likely re-order within 10-15 days based on cycle; estimate ₹80K-₹1.2L across preferred brands.",
        "credit_risk_score": risk,
        "payment_behaviour_score": pay,
        "recovery_approach": "Schedule a visit, offer a 7-day window with a 1% early-payment discount if overdue >30 days.",
        "upsell_suggestions": ["Boat Airdopes 141 — fast moving", "Noise ColorFit Pulse 3 — entry smartwatch", "Logitech M185 — accessories filler"],
        "pitch_points": ["Q1 scheme makes volume orders 10% cheaper", "Festival demand peak in next 3 weeks", "Free POS display on ₹1L+ Mivi order"],
        "best_visit_time": "Tuesday or Thursday between 11 AM - 1 PM (lowest shop foot traffic)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_or_generate_insights(db, customer_id: str, force: bool = False) -> dict:
    """Cache-aware insights fetch. Re-generate if >6 hours old."""
    cached = await db.ai_insights.find_one({"customer_id": customer_id}, {"_id": 0})
    if cached and not force:
        gen = cached.get("generated_at")
        if gen:
            try:
                gen_dt = datetime.fromisoformat(gen)
                if datetime.now(timezone.utc) - gen_dt < timedelta(hours=6):
                    return cached
            except Exception:
                pass

    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        return {}
    invoices = await db.invoices.find({"customer_id": customer_id}, {"_id": 0}).to_list(200)
    payments = await db.payments.find({"customer_id": customer_id}, {"_id": 0}).to_list(200)

    insights = await generate_customer_insights(customer, invoices, payments)
    await db.ai_insights.replace_one(
        {"customer_id": customer_id},
        insights,
        upsert=True,
    )
    return insights
