from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
from .intervals import Interval, RelativeAge
from .units import Unit


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


@dataclass
class AgeModelSurface:
    """A model surface has an arbitrary number of units below and above"""

    position: float
    units: list[Unit]
    boundary_status: BoundaryStatus

    @property
    def units_above(self):
        return [u for u in self.units if u.b_pos == self.position]

    @property
    def units_below(self):
        return [u for u in self.units if u.t_pos == self.position]

    def age_estimates(self):
        for u in self.units_above:
            if u.b_age is None:
                continue
            yield u.b_age
        for u in self.units_below:
            if u.t_age is None:
                continue
            yield u.t_age

    @property
    def relative_age(self) -> RelativeAge | None:
        ages = list(self._age_estimates())
        if len(ages) == 0:
            return None
        model_ages = [a.model_age() for a in ages]
        # Check that all ages are the same
        assert len(set(model_ages)) == 1
        # Rank the ages by which is the most specific
        ages.sort(key=lambda x: x.interval.age_span)
        return ages[0]

    @property
    def model_age(self) -> float:
        return self.relative_age.model_age()


def timescale_intervals(timescale_id: int):
    intervals = get_intervals()
    return [i for i in intervals if timescale_id in i.timescales]


class AgeModel:
    surfaces: list[AgeModelSurface]

    # Intervals that can be used for linking new relative surfaces
    _match_intervals: set[Interval]

    def __init__(self, surfaces: list[AgeModelSurface], timescale=11):
        self.surfaces = sorted(surfaces, key=lambda s: s.position)
        # Get all intervals defined in surfaces
        for surface in self.constrained_surfaces:
            for est in surface.age_estimates():
                self._match_intervals.add(est.interval)
        # Sort intervals by age span (smallest first)
        self._match_intervals = sorted(self._match_intervals, key=lambda i: i.age_span)
        self._match_intervals += sorted(
            timescale_intervals(timescale), key=lambda i: i.age_span
        )

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

        x = [s.position for s in self.constrained_surfaces]
        y = [s.model_age for s in self.constrained_surfaces]
        # A one-degree b-spline is a piecewise linear interpolator
        # Natural boundary conditions arbitrarily extend the domain
        # in either direction
        return make_interp_spline(x, y, k=1, bc_type="natural")

    def _containing_interval(self, age: float):
        # Find the first _match_interval that contains the age
        for interval in self._match_intervals:
            if interval.contains(age):
                return interval
        assert False, f"No interval found for age {age}"

    def apply(self) -> list[AgeModelSurface]:
        """Apply the model to unconstrained surfaces"""

        for surface in self.surfaces:
            model_age = self._linear_interpolator(surface.position)
            if surface.relative_age is None:
                interpolated_age = self._linear_interpolator(surface.position)
                interval = self._containing_interval(interpolated_age)
                proportion = interval.relative_position(interpolated_age)

                # Build relative age
                surface.relative_age = RelativeAge(interval, proportion)
                surface.boundary_status = BoundaryStatus.MODELED
            else:
                surface.boundary_status = BoundaryStatus.RELATIVE
            # Sanity check
            assert surface.relative_age.model_age() == model_age

        return self.surfaces


def get_nearest_interval(age: float, interval: Interval):
    """Get the nearest interval of an age type"""
    rank = interval.rank


def build_age_model(db, units: list[Unit]):
    """Build an age model for a column"""
    # Group by section_id
    sections = defaultdict(list)
    for unit in units:
        sections[unit.section_id].append(unit)

    for units in sections.values():
        build_section_age_model(db, units)


def build_section_age_model(db, units: list[Unit]) -> list[UnitBoundary]:
    """Build an age model for a section"""

    # Build an index of surfaces by position
    surfaces = defaultdict(list)
    for unit in units:
        surfaces[unit.b_pos].append(unit)
        surfaces[unit.t_pos].append(unit)

    surfaces = [AgeModelSurface(pos, units) for pos, units in surfaces.items()]

    model = AgeModel(surfaces)
    return list(create_unit_boundaries(model.apply()))


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
                    section_id=surface.units[0].section_id,
                    position=surface.position,
                    unit_above=above.id if above is not None else None,
                    unit_below=below.id if below is not None else None,
                )
