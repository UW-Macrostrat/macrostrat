"""Shared enums for the requests-per-day plot.

Used both as the CLI argument types and for the plot's own parameter resolution,
so the choices and their resolved values live in one place (no parallel mappings
to keep in sync). Lightweight on purpose — imported at CLI startup, unlike the
heavy `plot` module.
"""

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
