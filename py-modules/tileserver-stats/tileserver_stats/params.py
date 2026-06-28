"""Shared enums for the requests-per-day plot.

Used both as the CLI argument types and for the plot's own parameter resolution,
so the choices and their resolved values live in one place (no parallel mappings
to keep in sync). Lightweight on purpose — imported at CLI startup, unlike the
heavy `plot` module.
"""

import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class Smoothing(str, Enum):
    """Rolling-mean window applied to the requests-per-day series."""

    none = "none"  # raw daily
    weekly = "weekly"  # 7-day mean
    monthly = "monthly"  # 30-day mean

    @property
    def window(self) -> int:
        """Rolling window in days (1 = no smoothing)."""
        return _SMOOTH_WINDOWS[self]


_SMOOTH_WINDOWS: dict[Smoothing, int] = {
    Smoothing.none: 1,
    Smoothing.weekly: 7,
    Smoothing.monthly: 30,
}


class TimeRange(str, Enum):
    """Lookback window for the plot."""

    last_month = "last-month"
    last_year = "last-year"
    last_5_years = "last-5-years"
    all = "all"

    @property
    def days(self) -> Optional[int]:
        """Lookback in days, or None for all time."""
        return _RANGE_DAYS[self]


_RANGE_DAYS: dict[TimeRange, Optional[int]] = {
    TimeRange.last_month: 30,
    TimeRange.last_year: 365,
    TimeRange.last_5_years: 365 * 5,
    TimeRange.all: None,
}

_YEAR_RE = re.compile(r"\d{4}")


def is_valid_range(value: str) -> bool:
    """Whether `value` is an acceptable `--range`: a `TimeRange` name or a year."""
    if _YEAR_RE.fullmatch(value):
        return True
    return value in {member.value for member in TimeRange}


def resolve_date_window(
    value: str, max_date: datetime
) -> tuple[Optional[datetime], Optional[datetime]]:
    """Resolve a `--range` value to (start, end) datetime bounds; None = unbounded.

    Polymorphic: accepts a `TimeRange` name (a lookback from the latest data
    date) or a 4-digit calendar year — e.g. "2026" → [2026-01-01, 2027-01-01).
    """
    if _YEAR_RE.fullmatch(value):
        year = int(value)
        return datetime(year, 1, 1), datetime(year + 1, 1, 1)
    days = TimeRange(value).days  # ValueError if not a known name
    if days is None:
        return None, None
    return max_date - timedelta(days=days), None
