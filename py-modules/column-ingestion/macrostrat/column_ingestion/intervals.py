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
        return self.age_bottom - self.age_top

    def contains(self, age: float) -> bool:
        return self.age_top <= age <= self.age_bottom

    def relative_position(self, age):
        """Get the proportion of an age relative to an interval (not clamped)"""
        age_rel_to_bottom = self.age_bottom - age
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
        return self.interval.age_bottom + self.proportion * self.interval.age_span
