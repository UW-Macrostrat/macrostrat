"""Provenance of age control survives the trip from unit to `unit_boundaries`.

Database-free: everything under test is pure dataclass and enum behaviour.
"""

from pytest import fixture

from macrostrat.column_ingestion.age_model.model import (
    AgeModelSurface,
    BoundaryStatus,
    _declared_status,
)
from macrostrat.column_ingestion.intervals import (
    Interval,
    RelativeAge,
    containing_interval,
    interval_cache,
)
from macrostrat.column_ingestion.units import Unit

TONIAN = Interval(1, "Tonian", 1000.0, 720.0, 3, "period", [11])
CRYOGENIAN = Interval(2, "Cryogenian", 720.0, 635.0, 3, "period", [11])
NEOPROTEROZOIC = Interval(3, "Neoproterozoic", 1000.0, 538.8, 2, "era", [11])

#: Narrowest-first, which is the order `containing_interval`'s contract depends on.
INTERVALS = sorted([NEOPROTEROZOIC, TONIAN, CRYOGENIAN], key=lambda i: i.age_span)


class TestContainingInterval:
    def test_returns_the_most_specific_interval_for_a_narrowest_first_list(self):
        assert containing_interval(INTERVALS, 800.0) is TONIAN

    def test_returns_none_outside_every_interval(self):
        """The honest answer — there is no interval to be relative to."""
        assert containing_interval(INTERVALS, 4000.0) is None

    def test_order_is_the_whole_policy(self):
        """Widest-first returns the era, not the period. The caller decides."""
        widest_first = sorted(INTERVALS, key=lambda i: -i.age_span)
        assert containing_interval(widest_first, 800.0) is NEOPROTEROZOIC


class TestSurfaceStatus:
    def _surface(self, status, *, constrained=True):
        age = RelativeAge(TONIAN, 0.5) if constrained else None
        unit = Unit(b_pos=0, t_pos=1, section_id=1)
        return AgeModelSurface(
            0, [unit], status, relative_age=age, infer_relative_age=False
        )

    def test_modeled_is_the_placeholder_and_becomes_relative(self):
        surface = self._surface(BoundaryStatus.MODELED)
        assert surface.boundary_status is BoundaryStatus.RELATIVE

    def test_a_declared_status_survives(self):
        """The regression this guards: an imposed boundary recorded as `relative`
        claims the source named an interval, which for GBDB is simply untrue."""
        surface = self._surface(BoundaryStatus.IMPOSED)
        assert surface.boundary_status is BoundaryStatus.IMPOSED

    def test_absolute_survives_too(self):
        surface = self._surface(BoundaryStatus.ABSOLUTE)
        assert surface.boundary_status is BoundaryStatus.ABSOLUTE

    def test_an_unconstrained_surface_keeps_its_placeholder(self):
        surface = self._surface(BoundaryStatus.MODELED, constrained=False)
        assert surface.boundary_status is BoundaryStatus.MODELED


class TestDeclaredStatus:
    def _unit(self, b_pos, t_pos, status, *, aged=True):
        age = RelativeAge(TONIAN, 0.5) if aged else None
        return Unit(b_pos=b_pos, t_pos=t_pos, b_age=age, t_age=age, age_status=status)

    def test_units_agreeing_on_provenance_set_the_surface_status(self):
        units = [
            self._unit(0, 10, BoundaryStatus.IMPOSED),
            self._unit(10, 20, BoundaryStatus.IMPOSED),
        ]
        assert _declared_status(10, units) is BoundaryStatus.IMPOSED

    def test_units_with_no_age_claim_nothing(self):
        units = [self._unit(0, 10, BoundaryStatus.IMPOSED, aged=False)]
        assert _declared_status(10, units) is BoundaryStatus.MODELED

    def test_disagreement_falls_back_to_the_placeholder(self):
        units = [
            self._unit(0, 10, BoundaryStatus.IMPOSED),
            self._unit(10, 20, BoundaryStatus.RELATIVE),
        ]
        assert _declared_status(10, units) is BoundaryStatus.MODELED

    def test_only_ages_bearing_on_this_surface_count(self):
        """A unit's `b_age` constrains its base and its `t_age` its top; a unit
        that merely spans the position claims nothing about it."""
        units = [self._unit(0, 20, BoundaryStatus.IMPOSED)]
        assert _declared_status(10, units) is BoundaryStatus.MODELED


class TestRelativeAgeFromAbsolute:
    """`from_absolute` needs intervals, not a database — `get_intervals` reads its
    context-local cache first, so seeding it stands in for a connection."""

    @fixture(autouse=True)
    def _intervals(self):
        token = interval_cache.set(INTERVALS)
        yield
        interval_cache.reset(token)

    def test_an_age_becomes_an_interval_plus_a_proportion(self):
        age = RelativeAge.from_absolute(None, 860.0)
        assert age.interval is TONIAN
        # 1000 -> 720; 860 is halfway.
        assert age.proportion == 0.5

    def test_the_round_trip_is_lossless(self):
        for value in (999.0, 860.0, 721.0, 700.0, 600.0):
            age = RelativeAge.from_absolute(None, value)
            assert age.model_age() == value

    def test_the_endpoints_land_on_the_bounds(self):
        assert RelativeAge.from_absolute(None, 1000.0).proportion == 0.0
        assert RelativeAge.from_absolute(None, 720.0).model_age() == 720.0

    def test_none_in_none_out(self):
        assert RelativeAge.from_absolute(None, None) is None

    def test_an_age_outside_the_timescale_has_no_interval_to_be_relative_to(self):
        assert RelativeAge.from_absolute(None, 4000.0) is None
