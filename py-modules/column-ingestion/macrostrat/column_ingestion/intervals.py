import re
from dataclasses import dataclass, field
from contextvars import ContextVar

from .database import get_all_intervals

interval_cache = ContextVar("interval_cache", default=None)


def get_intervals():
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
        for row in get_all_intervals()
    ]
    interval_cache.set(_interval_cache)
    return _interval_cache


def get_interval_by_id(id: int | None):
    if id is None:
        return None
    return next((i for i in get_intervals() if i.id == id), None)


@dataclass
class IntervalID:
    id: int
    name: str

    def __hash__(self):
        return hash(self.id, self.name)


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
        return hash(self.id, self.name)

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


def split_text(text: str):
    """Split text by commas and/or >"""
    res = re.split(r"[,>]", text)
    return [x.strip() for x in res if x.strip()]


def get_interval_from_text(text: str | None):
    """Get the interval for a given text"""
    if text is None:
        return None

    all_intervals = get_intervals()

    ints = []
    for _int in split_text(text):
        a = _int.strip()
        # Check if the interval is an integer:
        match = next((i for i in all_intervals if match_predicate(i, a)), None)
        if match:
            ints.append(match)
        else:
            print(f"No match for {a}")

    # Order by age width descending
    ints.sort(key=lambda i: (i.age_bottom - i.age_top), reverse=True)
    # Ensure that intervals all overlap
    last_int = ints[-1]
    for _int in ints[:-1]:
        assert _int.age_bottom >= last_int.age_top
        assert _int.age_top <= last_int.age_bottom
    return last_int


def match_predicate(interval: Interval, text: str):
    if text.isdigit():
        return int(text) == interval.id
    return interval.name == text
