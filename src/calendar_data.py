"""
Static calendar data for FOMC meetings.
Defines total calendar days (n_m) and decision announcement days (m_m).
"""

CALENDAR_2026 = [
    {"month": 1, "days_in_month": 31, "decision_day": 28},    # Jan 27-28
    {"month": 2, "days_in_month": 28, "decision_day": None},  # Anchor
    {"month": 3, "days_in_month": 31, "decision_day": 18},    # Mar 17-18
    {"month": 4, "days_in_month": 30, "decision_day": 29},    # Apr 28-29
    {"month": 5, "days_in_month": 31, "decision_day": None},  # Anchor (NO meeting)
    {"month": 6, "days_in_month": 30, "decision_day": 17},    # Jun 16-17
    {"month": 7, "days_in_month": 31, "decision_day": 29},    # Jul 28-29
    {"month": 8, "days_in_month": 31, "decision_day": None},  # Anchor
    {"month": 9, "days_in_month": 30, "decision_day": 16},    # Sep 15-16
    {"month": 10, "days_in_month": 31, "decision_day": None}, # Anchor
    {"month": 11, "days_in_month": 30, "decision_day": 5},    # Nov 4-5
    {"month": 12, "days_in_month": 31, "decision_day": 16},   # Dec 15-16
]