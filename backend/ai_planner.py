"""AI route planner + performance analysis using Emergent LLM Key (Claude Sonnet 4.5)."""
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


async def generate_route_plan(user: dict, customers: list, max_stops: int = 10) -> dict:
    """AI-prioritised route plan for a salesperson based on LIVE customer data."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")

    # Build compact dataset
    stops = []
    for c in customers:
        if not c.get("lat") or not c.get("lng"):
            continue
        stops.append({
            "id": c["id"],
            "name": c["name"],
            "area": c.get("area"),
            "outstanding": c.get("outstanding", 0),
            "overdue": c.get("overdue", 0),
            "last_visit": (c.get("last_visit_date") or "")[:10],
            "last_order": (c.get("last_order_date") or "")[:10],
            "credit_risk": c.get("credit_risk_score", 50),
            "brands": c.get("brand_preferences", []),
            "lat": round(c["lat"], 4),
            "lng": round(c["lng"], 4),
        })

    if not stops:
        return {"plan": [], "summary": "No mappable customers found", "generated_at": datetime.now(timezone.utc).isoformat()}

    # Deterministic ranking fallback always available
    fallback = _fallback_route_plan(user, stops, max_stops)
    if not api_key:
        return fallback

    system_message = (
        "You are an expert beat-route planner for B2B field sales in Mumbai. "
        "Given a list of customers with outstanding, overdue, last-visit and coordinates, "
        "produce an optimised daily route ranked by recovery urgency × sales opportunity, "
        "clustered geographically. Respond with VALID JSON only."
    )

    payload = json.dumps({"salesperson": user.get("name"), "territory": user.get("territory"), "stops": stops[:25]}, default=str)

    user_prompt = f"""Inputs:
{payload}

Return JSON:
{{
  "summary": "<1-2 sentence brief>",
  "plan": [
    {{"order": 1, "customer_id": "<id>", "reason": "<one line why first>", "objective": "collection|pitch|relationship", "suggested_time": "10:30 AM"}},
    ...
  ]
}}
Limit plan to {max_stops} stops, prefer geographic clustering."""

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"route-{user['id']}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            system_message=system_message,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")

        response = await chat.send_message(UserMessage(text=user_prompt))
        text = response.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip("` \n")
        data = json.loads(text)

        # Enrich plan with full customer object
        cust_by_id = {c["id"]: c for c in customers}
        enriched = []
        for item in data.get("plan", [])[:max_stops]:
            cust = cust_by_id.get(item.get("customer_id"))
            if not cust:
                continue
            enriched.append({**item, "customer": cust})
        data["plan"] = enriched
        data["generated_at"] = datetime.now(timezone.utc).isoformat()
        return data
    except Exception as e:
        logger.exception("AI route plan failed: %s", e)
        return fallback


def _fallback_route_plan(user: dict, stops: list, max_stops: int) -> dict:
    cust_by_id = {s["id"]: s for s in stops}
    ranked = sorted(stops, key=lambda s: (-s["overdue"], -s["outstanding"]))[:max_stops]
    plan = []
    for i, s in enumerate(ranked):
        reason = "High overdue + outstanding" if s["overdue"] > 0 else "High outstanding"
        objective = "collection" if s["overdue"] > 0 else "pitch"
        plan.append({
            "order": i + 1,
            "customer_id": s["id"],
            "reason": reason,
            "objective": objective,
            "suggested_time": ["10:00 AM", "11:00 AM", "12:00 PM", "01:30 PM", "02:30 PM", "03:30 PM", "04:30 PM", "05:30 PM"][i % 8],
            "customer": s,
        })
    return {
        "summary": f"Priority route for {user.get('name')}: {len(plan)} stops focused on overdue recovery first, then geographic cluster.",
        "plan": plan,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def generate_performance_analysis(user: dict, target: dict, invoices: list, payments: list, visits: list) -> dict:
    """AI-generated performance critique + coaching for a salesperson based on LIVE data."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")

    # Compute concise metrics
    target_amt = target.get("target_amount", 0) if target else 0
    achieved = target.get("achieved_amount", 0) if target else 0
    pct = round((achieved / target_amt * 100) if target_amt else 0, 1)

    brand_sales = {}
    for inv in invoices:
        b = inv.get("brand", "Other")
        brand_sales[b] = brand_sales.get(b, 0) + inv.get("amount", 0)

    metrics = {
        "name": user.get("name"),
        "territory": user.get("territory"),
        "target_inr": target_amt,
        "achieved_inr": achieved,
        "achievement_pct": pct,
        "invoice_count_30d": len(invoices),
        "payment_count_30d": len(payments),
        "visit_count_30d": len(visits),
        "brand_split": brand_sales,
    }

    fallback = _fallback_performance(metrics)
    if not api_key:
        return fallback

    system_message = (
        "You are a sales coach for a B2B electronics distributor. Analyse the salesperson's "
        "live month-to-date performance and return concise, actionable JSON only."
    )

    user_prompt = f"""Live metrics:
{json.dumps(metrics, default=str, indent=2)}

Return JSON:
{{
  "summary": "<2-3 sentence performance summary>",
  "rating": "exceptional|on_track|behind|critical",
  "strengths": ["<bullet>", "<bullet>"],
  "gaps": ["<bullet>", "<bullet>"],
  "next_actions": ["<concrete action 1>", "<action 2>", "<action 3>"],
  "predicted_month_end_pct": <integer 0-200>
}}"""

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"perf-{user['id']}-{datetime.now(timezone.utc).strftime('%Y%m%d%H')}",
            system_message=system_message,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        response = await chat.send_message(UserMessage(text=user_prompt))
        text = response.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip("` \n")
        data = json.loads(text)
        data["metrics"] = metrics
        data["generated_at"] = datetime.now(timezone.utc).isoformat()
        return data
    except Exception as e:
        logger.exception("AI performance failed: %s", e)
        return fallback


def _fallback_performance(metrics: dict) -> dict:
    pct = metrics["achievement_pct"]
    if pct >= 100:
        rating = "exceptional"
    elif pct >= 75:
        rating = "on_track"
    elif pct >= 50:
        rating = "behind"
    else:
        rating = "critical"
    return {
        "summary": f"{metrics['name']} is at {pct}% of monthly target with {metrics['visit_count_30d']} visits in last 30 days.",
        "rating": rating,
        "strengths": ["Active field presence" if metrics["visit_count_30d"] > 10 else "Consistent invoice flow"],
        "gaps": ["Improve collection cadence" if pct < 80 else "Diversify brand portfolio"],
        "next_actions": [
            "Schedule visits to top-3 overdue accounts this week",
            "Push Q1 schemes to dormant customers (no order > 30 days)",
            "Increase Logitech/Mivi attach on Boat-led orders",
        ],
        "predicted_month_end_pct": int(min(200, pct * 1.15)),
        "metrics": metrics,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
