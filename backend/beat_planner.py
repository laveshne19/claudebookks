"""Beat-day planner.

Parses the free-text beat_days field on each customer (eg "Mon, Thu" or
"Sat (weekly) + Wed (alt)" or "Fri (1st & 3rd week)") and decides whether
a given customer should be visited TODAY.

Then ranks today's visits by tier × outstanding × time-since-last-visit.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import re

DAY_TOKENS = {
    "mon": 0, "monday": 0,
    "tue": 1, "tues": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thur": 3, "thurs": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}

TIER_RANK = {"PLATINUM": 4, "DIAMOND": 3, "GOLD": 2, "SILVER": 1}


def _matches_today(beat_days: str, now: Optional[datetime] = None) -> bool:
    """Return True if today's weekday is covered by beat_days, including alt-week / weekly rules."""
    if not beat_days:
        return False
    now = now or datetime.now(timezone.utc)
    weekday = now.weekday()  # Mon=0 .. Sun=6
    # Week-of-month: 1st Sunday's date / 7
    week_of_month = (now.day - 1) // 7 + 1  # 1..5
    is_odd_week = week_of_month % 2 == 1

    s = beat_days.lower()

    # Find tokens like "mon", "thu" and qualify by parenthetical rule
    # Strategy: walk through segments separated by , + ; "and"
    segments = re.split(r"[,+;]| and ", s)
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        # find day token in this segment
        day_idx = None
        for tok, idx in DAY_TOKENS.items():
            if re.search(rf"\b{tok}\b", seg):
                day_idx = idx
                break
        if day_idx is None or day_idx != weekday:
            continue

        # qualifier parsing
        if "weekly" in seg or "(weekly)" in seg:
            return True
        m = re.search(r"\(([^)]*)\)", seg)
        if not m:
            # plain "mon" or "thu" → every week
            return True
        qual = m.group(1).lower()
        if "weekly" in qual:
            return True
        if "alt" in qual:
            return is_odd_week  # treat 'alt' as odd weeks; close enough for planning
        # numbered weeks "1st & 3rd week" / "2nd & 4th"
        nums = []
        for word, n in [("1st", 1), ("2nd", 2), ("3rd", 3), ("4th", 4), ("5th", 5)]:
            if word in qual:
                nums.append(n)
        if nums:
            return week_of_month in nums
        # default → treat as weekly
        return True
    return False


def _days_since(iso_str: Optional[str], now: datetime) -> int:
    if not iso_str:
        return 999
    try:
        d = datetime.fromisoformat(iso_str)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (now - d).days
    except Exception:
        return 999


def build_today_beat(customers: list, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    weekday_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][now.weekday()]

    today_list = []
    for c in customers:
        if _matches_today(c.get("beat_days") or "", now):
            score = (
                TIER_RANK.get(c.get("tier") or "", 0) * 1000
                + min(c.get("overdue", 0), 1_000_000) / 1000
                + min(_days_since(c.get("last_visit_date"), now), 60) * 5
            )
            today_list.append({**c, "_score": score})

    today_list.sort(key=lambda x: -x["_score"])

    summary = {
        "weekday": weekday_name,
        "date": now.strftime("%Y-%m-%d"),
        "count": len(today_list),
        "platinum": len([c for c in today_list if c.get("tier") == "PLATINUM"]),
        "diamond": len([c for c in today_list if c.get("tier") == "DIAMOND"]),
        "gold": len([c for c in today_list if c.get("tier") == "GOLD"]),
        "silver": len([c for c in today_list if c.get("tier") == "SILVER"]),
        "total_outstanding": round(sum(c.get("outstanding", 0) for c in today_list), 0),
        "total_overdue": round(sum(c.get("overdue", 0) for c in today_list), 0),
    }

    # Strip internal _score field
    for c in today_list:
        c.pop("_score", None)

    return {"summary": summary, "stops": today_list}
