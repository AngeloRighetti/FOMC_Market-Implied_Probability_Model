"""
Dynamic calendar data for active FOMC policy meetings (2026-2027 rolling horizon).
Defines calendar days (n_m) and decision announcement days (m_m).
"""

from datetime import date
from typing import Any

# Active FOMC calendar covering the 12-month policy trajectory
FOMC_CALENDAR = [
    {"year": 2026, "month": 12, "days_in_month": 31, "decision_day": 9},    # Dec 09, 2026
    {"year": 2027, "month": 1,  "days_in_month": 31, "decision_day": 27},   # Jan 27, 2027
    {"year": 2027, "month": 2,  "days_in_month": 28, "decision_day": None}, # Anchor (No meeting)
    {"year": 2027, "month": 3,  "days_in_month": 31, "decision_day": 17},   # Mar 17, 2027
    {"year": 2027, "month": 4,  "days_in_month": 30, "decision_day": 28},   # Apr 28, 2027
    {"year": 2027, "month": 5,  "days_in_month": 31, "decision_day": None}, # Anchor (No meeting)
    {"year": 2027, "month": 6,  "days_in_month": 30, "decision_day": 9},    # Jun 09, 2027
    {"year": 2027, "month": 7,  "days_in_month": 31, "decision_day": 28},   # Jul 28, 2027
    {"year": 2027, "month": 8,  "days_in_month": 31, "decision_day": None}, # Anchor (No meeting)
    {"year": 2027, "month": 9,  "days_in_month": 30, "decision_day": 15},   # Sep 15, 2027
    {"year": 2027, "month": 10, "days_in_month": 31, "decision_day": 27},   # Oct 27, 2027
]


def get_active_calendar(as_of: date | None = None) -> list[dict[str, Any]]:
    """
    Returns upcoming calendar months from the observation date onward.
    """
    if as_of is None:
        as_of = date.today()

    return [
        m for m in FOMC_CALENDAR
        if (m["year"] > as_of.year) or (m["year"] == as_of.year and m["month"] >= as_of.month)
    ]