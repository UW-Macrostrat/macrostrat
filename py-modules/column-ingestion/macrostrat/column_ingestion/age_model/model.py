from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

import numpy as N
from rich import print

from macrostrat.utils import get_logger

from ..intervals import Interval, RelativeAge, get_intervals
from ..reconciliation import ReconciliationPlan
from ..units import Unit
from .reconciliation import reconcile_unit_boundaries, write_unit_boundaries

log = get_logger(__name__)


class BoundaryStatus(Enum):
    MODELED = "modeled"
    RELATIVE = "relative"
    ABSOLUTE = "absolute"


@dataclass
class UnitBoundary:
    age: RelativeAge
    model_age: float
    boundary_status: BoundaryStatus
    section_id: int
    # Position is useful for measured columns
    position: float | None = None
    unit_above: int | None = None
    unit_below: int | None = None

    # Validate that the boundary is valid
    def __post_init__(self):
        if self.unit_above is None and self.unit_below is None:
            raise ValueError("Either unit_above or unit_below must be set")

    # allow conversion to dict
    def to_dict(self):
        return {
            "t1": self.age.interval.id,
            "t1_prop": self.age.proportion,
            "t1_age": self.model_age,
            "unit_id": self.unit_below,
            "unit_id_2": self.unit_above,
            "boundary_status": self.boundary_status.value,
            "boundary_position": self.position,
            "section_id": self.section_id,
        }


@dataclass
class AgeModelSurface:
    """A model surface has an arbitrary number of units below and above"""

    position: float
    units: list[Unit]
    boundary_status: BoundaryStatus
    relative_age: RelativeAge | None = None
    # Explicit unit adjacency, for surfaces that cannot be recovered by matching
    # positions (again: gaps and overlaps between successive units).
    above: list[Unit] | None = None
    below: list[Unit] | None = None
    # Whether to fall back to the adjacent units' own `b_age`/`t_age` when no
    # relative age is given. Callers that derive constraints themselves (e.g.
    # `eodp_age_model`, where the constraint belongs to a run of units rather
    # than to any single one) set this False so unconstrained surfaces stay
    # unconstrained and get modeled instead.
    infer_relative_age: bool = True

    def __post_init__(self):
        # Set relative age if not provided
        if self.relative_age is None and self.infer_relative_age:
            self.relative_age = self.build_relative_age()
        if self.relative_age is not None:
            self.boundary_status = BoundaryStatus.RELATIVE

    @property
    def units_above(self):
        if self.above is not None:
            return list(self.above)
        return [u for u in self.units if u.b_pos == self.position]

    @property
    def units_below(self):
        if self.below is not None:
            return list(self.below)
        return [u for u in self.units if u.t_pos == self.position]

    @property
    def section_id(self) -> int | None:
        for u in [*self.units, *(self.above or []), *(self.below or [])]:
            if u is not None:
                return u.section_id
        return None

    def age_estimates(self):
        for u in self.units_above:
            if u.b_age is None:
                continue
            yield u.b_age
        for u in self.units_below:
            if u.t_age is None:
                continue
            yield u.t_age

    def build_relative_age(self) -> RelativeAge | None:
        ages = list(self.age_estimates())
        if len(ages) == 0:
            return None
        model_ages = [a.model_age() for a in ages]
        # Check that all ages are the same
        if len(set(model_ages)) > 1:
            print(f"[yellow bold]Warning: model ages are not all the same: {ages}")
        # Rank the ages by which is the most specific
        ages.sort(key=lambda x: x.interval.age_span)
        return ages[0]

    @property
    def model_age(self) -> float:
        return self.relative_age.model_age()

    def __str__(self):
        units_above = ",".join([str(u.id) for u in self.units_above])
        units_below = ",".join([str(u.id) for u in self.units_below])
        return f"AgeModelSurface(position={self.position}, relative_age={self.relative_age}, above={units_above}, below={units_below})"

    def __hash__(self):
        return hash((self.position, self.relative_age))


def timescale_intervals(db, timescale_id: int):
    intervals = get_intervals(db)
    return [i for i in intervals if timescale_id in i.timescales]


class AgeModel:
    surfaces: list[AgeModelSurface]

    # Intervals that can be used for linking new relative surfaces
    _match_intervals: list[Interval]

    def __init__(self, db, surfaces: list[AgeModelSurface], timescale=11):
        # Sorted on the modeling axis, which the interpolator requires to be
        # increasing.
        self.surfaces = sorted(surfaces, key=self.axis_position)

        # Get all intervals defined in surfaces
        self._match_intervals = list()
        for surface in self.constrained_surfaces:
            self._match_intervals.append(surface.relative_age.interval)
            for est in surface.age_estimates():
                self._match_intervals.append(est.interval)
        # Sort intervals by age span (smallest first)
        self._match_intervals = sorted(self._match_intervals, key=lambda i: i.age_span)
        self._match_intervals += sorted(
            timescale_intervals(db, timescale), key=lambda i: i.age_span
        )

    def axis_position(self, surface: AgeModelSurface) -> float:
        """The coordinate this model spreads time along.

        The measured position, which is the principled default: time advances
        through section in proportion to how much section there is. Subclasses
        override this where a column's positions mean something else — an ordinal
        column has no metric distance between its units, and a borehole with
        unrecovered core has a choice to make about the gaps.

        An override must be monotonic in the same direction as age, since the
        interpolator needs an increasing axis.
        """
        return surface.position

    @property
    def has_valid_age_model(self):
        # Two constraints at the same axis position cannot define a model, so
        # count distinct positions rather than surfaces.
        return len({self.axis_position(s) for s in self.constrained_surfaces}) >= 2

    @property
    def constrained_surfaces(self):
        return [s for s in self.surfaces if s.relative_age is not None]

    def fit_surface(
        self,
        surface: AgeModelSurface,
    ):
        """Fit an unconstrained surface to the model"""
        pass

    @property
    def _linear_interpolator(self):
        from scipy.interpolate import make_interp_spline

        # Coincident axis positions are possible — a zero-thickness unit puts two
        # surfaces at the same coordinate — and a spline cannot represent a step.
        # Collapse them, keeping the last (oldest) age so the model stays
        # monotonic below the collapsed point. Surfaces are already sorted.
        x, y = [], []
        for surface in self.constrained_surfaces:
            position = self.axis_position(surface)
            if x and position == x[-1]:
                y[-1] = surface.model_age
                continue
            x.append(position)
            y.append(surface.model_age)
        # A one-degree b-spline is a piecewise linear interpolator
        # Natural boundary conditions arbitrarily extend the domain
        # in either direction
        return make_interp_spline(x, y, k=1, bc_type=None)

    def _containing_interval(self, age: float):
        # Find the first _match_interval that contains the age
        for interval in self._match_intervals:
            if interval.contains(age):
                return interval
        assert False, f"No interval found for age {age}"

    def apply(self) -> list[AgeModelSurface]:
        """Apply the model to unconstrained surfaces"""

        for surface in self.surfaces:
            position = self.axis_position(surface)
            model_age = self._linear_interpolator(position)
            if surface.relative_age is None:
                interpolated_age = self._linear_interpolator(position)
                interval = self._containing_interval(interpolated_age)
                proportion = interval.relative_position(interpolated_age)

                # Build relative age
                surface.relative_age = RelativeAge(interval, proportion)
                surface.boundary_status = BoundaryStatus.MODELED
            else:
                surface.boundary_status = BoundaryStatus.RELATIVE
            # Sanity check
            if surface.relative_age is not None:
                assert N.allclose(
                    float(surface.relative_age.model_age()), float(model_age)
                )

        return self.surfaces


def get_nearest_interval(age: float, interval: Interval):
    """Get the nearest interval of an age type"""
    rank = interval.rank


def build_age_model(db, units: list[Unit]) -> dict[int, ReconciliationPlan]:
    """Build the age model for every section represented in `units`.

    Idempotent: reconciles against the existing boundaries, so re-running over an
    unchanged column is a no-op. Returns the plan per section.
    """
    sections = defaultdict(list)
    for unit in units:
        sections[unit.section_id].append(unit)

    plans = {}
    for section_id, section_units in sections.items():
        plan = build_section_age_model(db, section_units)
        if plan is not None:
            plans[section_id] = plan
    return plans


def _build_section_age_model(db, units: list[Unit]):
    """Build an age model for a section"""

    # Build an index of surfaces by position
    surfaces = defaultdict(list)
    for unit in units:
        surfaces[unit.b_pos].append(unit)
        surfaces[unit.t_pos].append(unit)

    surfaces = [
        AgeModelSurface(pos, units, BoundaryStatus.MODELED)
        for pos, units in surfaces.items()
    ]

    # TODO: we only need the db to grab timescale intervals
    model = AgeModel(db, surfaces)

    if not model.has_valid_age_model:
        # The message said "skipping" but execution continued, and `apply()` then
        # failed inside the interpolator with an empty knot list.
        log.warning(
            "Section %s: fewer than two distinct age constraints; "
            "skipping unit_boundaries",
            units[0].section_id if units else None,
        )
        return []

    return list(create_unit_boundaries(model.apply()))


def build_section_age_model(db, units: list[Unit]) -> ReconciliationPlan | None:
    """Build a section's age model and reconcile it into `unit_boundaries`.

    Reconciles rather than inserting blindly. That used to be safe only because the
    caller deleted the section's units first, which cascaded the old boundaries away;
    now that units are preserved across a re-import, a plain insert would double the
    boundary set on every run.
    """
    if not units:
        return None
    boundaries = _build_section_age_model(db, units)
    if not boundaries:
        # Don't reconcile an empty model — that reads as "delete everything".
        return None
    return reconcile_unit_boundaries(db, units[0].section_id, boundaries)


def create_unit_boundaries(surfaces: list[AgeModelSurface]):
    for surface in surfaces:
        # Create unit_boundaries entries linking each set of units
        units_above = surface.units_above
        units_below = surface.units_below
        if len(units_above) == 0:
            units_above.append(None)
        if len(units_below) == 0:
            units_below.append(None)

        for above in units_above:
            for below in units_below:
                yield UnitBoundary(
                    age=surface.relative_age,
                    model_age=surface.model_age,
                    boundary_status=surface.boundary_status,
                    section_id=surface.section_id,
                    position=surface.position,
                    unit_above=above.id if above is not None else None,
                    unit_below=below.id if below is not None else None,
                )


def get_units_for_column(db, column_id: int) -> list[Unit]:
    db.automap(schemas=["macrostrat"])
    U = db.model.macrostrat_units
    units = db.session.query(U).filter(U.col_id == column_id).all()
    for unit in units:
        yield Unit(
            id=unit.id,
            col_id=unit.col_id,
            section_id=unit.section_id,
            b_pos=unit.position_bottom,
            t_pos=unit.position_top,
        )


def build_age_model_for_existing_column(db, column_id: int, *, dry_run: bool = False):
    """Rebuild the age model for every section of a column.

    Idempotent: reconciles against the existing boundaries rather than dropping
    and recreating them, so re-running on an unchanged column is a no-op and
    surfaces that did not move keep their `id` and curated columns.
    """
    db.automap(schemas=["macrostrat"])
    units = list(get_units_for_column(db, column_id))
    section_ids = sorted({u.section_id for u in units})

    plans = {}
    with db.transaction():
        for section_id in section_ids:
            section_units = [u for u in units if u.section_id == section_id]
            boundaries = _build_section_age_model(db, section_units)
            if not boundaries:
                # Reconciling an empty model would delete the section's existing
                # boundaries, which is the opposite of what a failed rebuild should
                # do. Leave them alone and say so.
                log.warning(
                    "Section %s: produced no boundaries; leaving existing ones intact",
                    section_id,
                )
                continue
            plans[section_id] = reconcile_unit_boundaries(
                db, section_id, boundaries, dry_run=dry_run
            )
    return plans


def remove_existing_age_model(db, section: int):
    """Delete a section's boundaries outright.

    Prefer `reconcile_unit_boundaries`, which preserves row identity and curated
    columns. This remains for the cases where the intent really is to clear a
    section — note it drops `paleo_lat`/`paleo_lng` along with everything else.
    """
    db.run_query(
        """
    DELETE FROM macrostrat.unit_boundaries
    WHERE section_id = :section
    """,
        dict(section=section),
    )
