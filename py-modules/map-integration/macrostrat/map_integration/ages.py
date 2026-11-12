"""Resolve a map unit's ages to `b_interval`/`t_interval`.

Interval names and numeric ages (Ma) both resolve against `macrostrat.intervals`.
Which source field to trust, and how a source's own age vocabulary maps onto
interval names, are judgments about a dataset and stay with its pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

__all__ = [
    "Interval",
    "MissingIntervals",
    "STANDARD_TIMESCALES",
    "interval_for_age",
    "named_intervals",
    "numeric_range",
    "span",
    "spanning_interval",
    "standard_intervals",
]

#: The global timescale at every rank, finest first.
STANDARD_TIMESCALES = (
    "international ages",
    "international epochs",
    "international periods",
    "international eras",
    "international eons",
)


@dataclass(frozen=True)
class Interval:
    id: int
    name: str
    age_bottom: float
    age_top: float

    @property
    def duration(self) -> float:
        return self.age_bottom - self.age_top


class MissingIntervals(ValueError):
    def __init__(self, names: Iterable[str]):
        self.names = sorted(names)
        super().__init__(f"Intervals not in macrostrat.intervals: {self.names}")


def _interval(row) -> Interval:
    return Interval(
        row.id, row.interval_name, float(row.age_bottom), float(row.age_top)
    )


def named_intervals(db, names: Iterable[str]) -> dict[str, Interval]:
    """Intervals by exact name, raising `MissingIntervals` for any absent.

    Where a name repeats across timescales, the lowest id wins.
    """
    names = sorted(set(names))
    found: dict[str, Interval] = {}
    for row in db.run_query(
        "SELECT id, interval_name, age_bottom, age_top FROM macrostrat.intervals "
        "WHERE interval_name = ANY(:names) ORDER BY id",
        dict(names=names),
    ):
        found.setdefault(row.interval_name, _interval(row))
    missing = set(names) - set(found)
    if missing:
        raise MissingIntervals(missing)
    return found


def standard_intervals(
    db, timescales: Iterable[str] = STANDARD_TIMESCALES
) -> list[Interval]:
    """Every interval in the named timescales, which a numeric age resolves against."""
    return [
        _interval(row)
        for row in db.run_query(
            """
            SELECT DISTINCT i.id, i.interval_name, i.age_bottom, i.age_top
            FROM macrostrat.intervals i
            JOIN macrostrat.timescales_intervals ti ON ti.interval_id = i.id
            JOIN macrostrat.timescales t ON t.id = ti.timescale_id
            WHERE t.timescale = ANY(:timescales)
            ORDER BY i.id
            """,
            dict(timescales=list(timescales)),
        )
    ]


def interval_for_age(
    age: float, intervals: Iterable[Interval], *, base: bool
) -> Interval | None:
    """The narrowest interval holding `age`.

    A base on a boundary belongs to the younger interval and a top to the older,
    so a unit dated 1000-720 Ma is Tonian, not Stenian to Cryogenian.
    """
    if base:
        fits = [i for i in intervals if i.age_top < age <= i.age_bottom]
    else:
        fits = [i for i in intervals if i.age_top <= age < i.age_bottom]
    return min(fits, key=lambda i: (i.duration, i.id), default=None)


def span(pairs: Iterable[tuple[Interval, Interval]]) -> tuple[Interval, Interval]:
    """Oldest base and youngest top over several `(b_interval, t_interval)` pairs."""
    pairs = list(pairs)
    b = max((b for b, _ in pairs), key=lambda i: i.age_bottom)
    t = min((t for _, t in pairs), key=lambda i: i.age_top)
    return b, t


def spanning_interval(
    b: Interval, t: Interval, intervals: Iterable[Interval]
) -> Interval | None:
    """The interval a `b`-`t` range covers exactly: Gelasian-Meghalayan is Quaternary."""
    if b == t:
        return None
    fits = [
        i for i in intervals if i.age_bottom == b.age_bottom and i.age_top == t.age_top
    ]
    return min(fits, key=lambda i: (i.duration, i.id), default=None)


def numeric_range(
    base: float, top: float, intervals: Iterable[Interval]
) -> tuple[Interval | None, Interval | None]:
    """`(b_interval, t_interval)` for a numeric age range, one interval if it covers one."""
    intervals = list(intervals)
    b = interval_for_age(base, intervals, base=True)
    t = interval_for_age(top, intervals, base=False)
    if b is None or t is None:
        return b, t
    whole = spanning_interval(b, t, intervals)
    return (whole, whole) if whole else (b, t)
