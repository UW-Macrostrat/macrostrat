from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Interval:
    id: int
    age_bottom: Decimal | float | None
    age_top: Decimal | float | None
    interval_name: str | None
    interval_abbrev: str | None = None
    interval_type: str | None = None
    interval_color: str | None = None
    rank: int | None = None
    timescales: list[int] | None = None


@dataclass(frozen=True)
class Lithology:
    id: int
    lith: str | None
    lith_type: str | None = None
    lith_class: str | None = None
    lith_fill: int | None = None
    comp_coef: Decimal | float | None = None
    initial_porosity: Decimal | float | None = None
    bulk_density: Decimal | float | None = None
    lith_color: str | None = None


@dataclass(frozen=True)
class LithologyAttribute:
    id: int
    lith_att: str | None
    att_type: str | None = None
    lith_att_fill: int | None = None


@dataclass(frozen=True)
class Environment:
    id: int
    environ: str | None
    environ_type: str | None = None
    environ_class: str | None = None
    environ_color: str | None = None
