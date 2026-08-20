"""Check the eODP `fo`/`lo` reconstruction against boundaries dumped from the database.

These run without a database: the fixtures under
`tests/fixtures/eodp/` carry the units, the intervals they reference,
and the legacy `unit_boundaries` rows to compare against.
"""

import csv
from pathlib import Path

from pytest import approx, fixture, mark

from macrostrat.column_ingestion.age_model.eodp import (
    EODPAgeModel,
    cumulative_thickness,
    eodp_surfaces,
    group_packages,
)
from macrostrat.column_ingestion.age_model.model import (
    BoundaryStatus,
    create_unit_boundaries,
)
from macrostrat.column_ingestion.intervals import Interval, RelativeAge
from macrostrat.column_ingestion.units import Unit

FIXTURES = Path(__file__).parents[1] / "fixtures" / "eodp"

# Sections dumped from the local database.
SECTIONS = {
    13768: "section-13768-site-960-hole-c",
    13807: "section-13807-site-963-hole-a",
    12220: "section-12220-single-package",
    12219: "section-12219-single-unit",
}


def _read(name):
    with open(FIXTURES / name) as f:
        return list(csv.DictReader(f))


@fixture(scope="module")
def intervals():
    return {
        int(row["id"]): Interval(
            int(row["id"]),
            row["interval_name"],
            float(row["age_bottom"]),
            float(row["age_top"]),
            int(row["rank"]),
            row["interval_type"],
        )
        for row in _read("intervals.csv")
    }


def _units(slug, intervals):
    units = []
    for row in _read(f"{slug}-units.csv"):
        unit = Unit(
            id=int(row["id"]),
            col_id=int(row["col_id"]),
            section_id=int(row["section_id"]),
            t_pos=float(row["position_top"]),
            b_pos=float(row["position_bottom"]),
        )
        unit.b_age = RelativeAge(intervals[int(row["fo"])], 0)
        unit.t_age = RelativeAge(intervals[int(row["lo"])], 1)
        units.append(unit)
    # Ordered by position_bottom: where units overlap this differs from
    # position_top order, and the legacy boundaries follow the former.
    return sorted(units, key=lambda u: u.b_pos)


class _OfflineEODPAgeModel(EODPAgeModel):
    """EODPAgeModel without the database, which the base class only needs to pull
    candidate intervals for naming modeled surfaces. Here every modeled age falls
    inside its own package, so the section's own intervals suffice."""

    def __init__(self, surfaces, units):
        coords = cumulative_thickness(units)
        self._thickness = {u.id: coords[i + 1] for i, u in enumerate(units)}
        self.surfaces = sorted(surfaces, key=self.axis_position)
        self._match_intervals = sorted(
            {s.relative_age.interval for s in surfaces if s.relative_age is not None},
            key=lambda i: i.age_span,
        )


def _apply(units, intervals, surfaces=None):
    if surfaces is None:
        surfaces = eodp_surfaces(units)
    return _OfflineEODPAgeModel(surfaces, units).apply()


@mark.parametrize("section_id", sorted(SECTIONS))
def test_reproduces_eodp_boundaries(section_id, intervals):
    """Positions, intervals and ages should match what the importer produced."""
    slug = SECTIONS[section_id]
    units = _units(slug, intervals)
    expected = sorted(
        _read(f"{slug}-boundaries.csv"), key=lambda r: float(r["boundary_position"])
    )

    surfaces = _apply(units, intervals)
    assert len(surfaces) == len(units) + 1 == len(expected)

    for surface, row in zip(surfaces, expected):
        assert surface.position == approx(float(row["boundary_position"]))
        assert surface.relative_age.interval.id == int(row["t1"])
        assert surface.relative_age.proportion == approx(
            float(row["t1_prop"]), abs=1e-5
        )
        assert surface.model_age == approx(float(row["t1_age"]), abs=1e-3)


@mark.parametrize("section_id", sorted(SECTIONS))
def test_unit_adjacency_matches(section_id, intervals):
    """`unit_id` is the deeper unit, `unit_id_2` the shallower. Legacy rows use 0
    as the "no unit" sentinel where we write None."""
    slug = SECTIONS[section_id]
    units = _units(slug, intervals)
    expected = sorted(
        _read(f"{slug}-boundaries.csv"), key=lambda r: float(r["boundary_position"])
    )

    boundaries = list(create_unit_boundaries(_apply(units, intervals)))
    boundaries.sort(key=lambda b: b.position)

    for boundary, row in zip(boundaries, expected):
        assert (boundary.unit_below or 0) == int(row["unit_id"])
        assert (boundary.unit_above or 0) == int(row["unit_id_2"])


@mark.parametrize("section_id", sorted(SECTIONS))
def test_only_the_eodp_specific_surfaces_are_constrained(section_id, intervals):
    """Stage 1 should assert as little as possible: package endpoints plus the
    base of the hole. Everything else is left for the general model."""
    slug = SECTIONS[section_id]
    units = _units(slug, intervals)

    surfaces = eodp_surfaces(units)
    constrained = {i for i, s in enumerate(surfaces) if s.relative_age is not None}

    packages = group_packages(units)
    assert constrained
    # At most two endpoints per package, plus the basal boundary.
    assert len(constrained) <= 2 * len(packages) + 1

    # Applying the model must not change *which* surfaces are relative: it fills
    # the rest in as modeled.
    applied = _apply(units, intervals, surfaces)
    assert len(applied) == len(surfaces)
    for i, surface in enumerate(applied):
        expected = (
            BoundaryStatus.RELATIVE if i in constrained else BoundaryStatus.MODELED
        )
        assert surface.boundary_status == expected, f"surface {i}"


def test_target_section_13767_extends_downward(intervals):
    """The new units at the base of Site 960 Hole A are one long Early Cretaceous
    package, so they fall entirely inside the last package. Check the model
    covers them and stays monotonic."""
    units = _units("section-13767-site-960-hole-a", intervals)
    assert len(units) == 58

    surfaces = _apply(units, intervals)
    assert len(surfaces) == 59

    ages = [s.model_age for s in surfaces]
    assert ages == sorted(ages), "ages must increase downward"

    # Base of the hole sits inside Early Cretaceous rather than on its limit.
    basal = surfaces[-1]
    assert basal.relative_age.interval.name == "Early Cretaceous"
    assert basal.relative_age.proportion == approx(2 / 3)
