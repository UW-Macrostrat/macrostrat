import re
from contextvars import ContextVar
from dataclasses import dataclass, field

from rich import print

from .database import get_all_intervals

#: Placeholder written into `units.fo` / `units.lo` by an ingest that has not yet built
#: an age model. `macrostrat.intervals` has no id `0`, and both columns are NOT NULL with
#: a FK to `intervals`, so a unit must reference *some* interval before its ages are
#: known. Interval 499 is "Precambrian-Phanerozoic" (4031–0 Ma) — the whole of geologic
#: time, and therefore unmistakably a non-answer rather than a plausible-looking one.
#:
#: This is a deliberate, named convention, not a magic number: `fo = UNMODELED_INTERVAL`
#: is the queryable predicate for "this column's age model has not been written yet".
#: Columns in that state carry `status_code = 'in process'` and so are excluded from the
#: published API and the lookup rebuild — **promoting one to 'active' should require a
#: real age model first.**
UNMODELED_INTERVAL = 499


interval_cache = ContextVar("interval_cache", default=None)


def get_intervals(db):
    _interval_cache = interval_cache.get()
    if _interval_cache is not None:
        return _interval_cache
    _interval_cache = [
        Interval(
            row.id,
            row.interval_name,
            row.age_bottom,
            row.age_top,
            row.rank,
            row.interval_type,
            row.timescales,
        )
        for row in get_all_intervals(db)
    ]
    interval_cache.set(_interval_cache)
    return _interval_cache


def get_interval_by_id(db, id: int | None):
    if id is None:
        return None
    return next((i for i in get_intervals(db) if i.id == id), None)


def timescale_intervals(db, timescale_id: int = 11):
    """Intervals belonging to a timescale, narrowest first.

    The sort order is what makes `containing_interval` return the *most specific*
    interval containing an age, which is the behaviour every caller wants.
    """
    intervals = [i for i in get_intervals(db) if timescale_id in i.timescales]
    return sorted(intervals, key=lambda i: i.age_span)


def containing_interval(intervals: list["Interval"], age: float) -> "Interval | None":
    """The first interval in `intervals` that contains `age`.

    Order is the caller's to decide, and it is the whole of the policy: pass a
    narrowest-first list to get the most specific interval.
    """
    return next((i for i in intervals if i.contains(float(age))), None)


@dataclass
class IntervalID:
    id: int
    name: str

    def __hash__(self):
        return hash((self.id, self.name))


@dataclass
class Interval:
    id: int
    name: str
    age_bottom: float
    age_top: float
    rank: int
    type: str
    timescales: list[int] = field(default_factory=list)

    @property
    def age_span(self) -> float:
        return float(self.age_bottom - self.age_top)

    def contains(self, age: float) -> bool:
        return self.age_top <= age <= self.age_bottom

    def relative_position(self, age):
        """Get the proportion of an age relative to an interval (not clamped)"""
        age_rel_to_bottom = float(self.age_bottom) - float(age)
        return age_rel_to_bottom / self.age_span

    def __hash__(self):
        return hash((self.id, self.name))

    def __eq__(self, other):
        return self.id == other.id and self.name == other.name


@dataclass
class RelativeAge:
    interval: Interval
    proportion: float

    def model_age(self) -> float:
        if self.proportion == 1:
            return self.interval.age_top
        return float(self.interval.age_bottom) - float(self.proportion) * float(
            self.interval.age_span
        )

    @classmethod
    def from_absolute(
        cls, db, age: float | None, *, timescale: int = 11
    ) -> "RelativeAge | None":
        """Express a known numeric age as an interval plus a proportion through it.

        Macrostrat stores age control as `(t1, t1_prop, t1_age)` and has no way to
        record a boundary that is not relative to an interval — so an age that is
        simply a number still has to name the interval it falls in. That is the
        inverse of the usual direction, and it is the convention the 177 existing
        `boundary_status = 'absolute'` rows already follow.

        Datasets needing this are not the exception they look like. ChinaLex has 33
        boundaries with no calibration expression, and GBDB has no dated surfaces at
        all — every age it yields is a number produced by thickness interpolation.
        Before this existed the arithmetic was reachable only from inside a
        constructed `AgeModel`, so callers that already knew the age reimplemented it.

        Returns `None` for an age outside the timescale, which is the honest answer:
        there is no interval to be relative to.
        """
        if age is None:
            return None
        interval = containing_interval(timescale_intervals(db, timescale), float(age))
        if interval is None:
            return None
        return cls(interval, interval.relative_position(float(age)))

    def __hash__(self):
        return hash((self.interval, self.proportion))


def split_text(text: str):
    """Split text by commas and/or >"""
    res = re.split(r"[,>]", text)
    return [x.strip() for x in res if x.strip()]


def get_interval_from_text(db, text: str | None):
    """Get the interval for a given text"""
    if text is None:
        return None

    all_intervals = get_intervals(db)

    ints = []
    for _int in split_text(text):
        a = _int.strip()
        # Check if the interval is an integer:
        match = next((i for i in all_intervals if match_predicate(i, a)), None)
        if match:
            ints.append(match)
        else:
            print(f"[red]No match for {a}")

    if len(ints) == 0:
        return None

    # Order by age width descending
    ints.sort(key=lambda i: i.age_bottom - i.age_top, reverse=True)
    # Ensure that intervals all overlap
    last_int = ints[-1]
    for _int in ints[:-1]:
        assert _int.age_bottom >= last_int.age_top
        assert _int.age_top <= last_int.age_bottom
    return last_int


def match_predicate(interval: Interval, text: str):
    if text.isdigit():
        return int(text) == interval.id
    return interval.name.lower() == text.lower()
