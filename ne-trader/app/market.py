"""Market-hours and trading-calendar helpers (IST).

Encapsulates Indian equity market session rules so the trader never acts
outside permitted hours:

- Regular session: 09:15 - 15:30 IST
- New-entry cutoff: 15:00 IST (spec risk rule)
- Hard square-off: 15:15 IST
- No weekends, no NSE holidays
"""

from __future__ import annotations

import datetime as dt
from typing import Set

import pytz

IST = pytz.timezone("Asia/Kolkata")

MARKET_OPEN = dt.time(9, 15)
MARKET_CLOSE = dt.time(15, 30)
NEW_ENTRY_CUTOFF = dt.time(15, 0)
SQUARE_OFF = dt.time(15, 15)

# NSE trading holidays (full-day) for 2026. Update annually.
NSE_HOLIDAYS_2026: Set[dt.date] = {
    dt.date(2026, 1, 26),   # Republic Day
    dt.date(2026, 3, 4),    # Holi
    dt.date(2026, 3, 21),   # Id-ul-Fitr (approx)
    dt.date(2026, 4, 1),    # Annual closing / Mahavir Jayanti window
    dt.date(2026, 4, 3),    # Good Friday
    dt.date(2026, 4, 14),   # Dr. Ambedkar Jayanti
    dt.date(2026, 5, 1),    # Maharashtra Day
    dt.date(2026, 8, 15),   # Independence Day
    dt.date(2026, 10, 2),   # Gandhi Jayanti
    dt.date(2026, 11, 9),   # Diwali / Laxmi Pujan window
    dt.date(2026, 12, 25),  # Christmas
}


def now_ist() -> dt.datetime:
    """Return the current timezone-aware datetime in IST."""
    return dt.datetime.now(IST)


def is_trading_day(when: dt.datetime | None = None) -> bool:
    """Return True if ``when`` (default now) is a weekday and not an NSE holiday.

    Args:
        when: Optional timezone-aware or naive datetime; defaults to now (IST).

    Returns:
        bool: True when the market trades on that calendar day.
    """
    moment = when or now_ist()
    day = moment.date()
    if moment.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return day not in NSE_HOLIDAYS_2026


def is_market_open(when: dt.datetime | None = None) -> bool:
    """Return True if the regular session is currently open (09:15-15:30 IST).

    Args:
        when: Optional datetime; defaults to now (IST).

    Returns:
        bool: True when within session hours on a trading day.
    """
    moment = when or now_ist()
    if not is_trading_day(moment):
        return False
    return MARKET_OPEN <= moment.time() <= MARKET_CLOSE


def can_open_new_position(when: dt.datetime | None = None) -> bool:
    """Return True if new entries are allowed (before the 15:00 IST cutoff)."""
    moment = when or now_ist()
    if not is_market_open(moment):
        return False
    return moment.time() < NEW_ENTRY_CUTOFF


def is_square_off_time(when: dt.datetime | None = None) -> bool:
    """Return True at/after the 15:15 IST hard square-off on a trading day."""
    moment = when or now_ist()
    if not is_trading_day(moment):
        return False
    return moment.time() >= SQUARE_OFF
