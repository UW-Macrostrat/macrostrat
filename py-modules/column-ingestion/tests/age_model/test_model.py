"""Tests for the interpolating age model itself."""

from macrostrat.column_ingestion.age_model import (
    AgeModel,
    AgeModelSurface,
    BoundaryStatus,
)
from macrostrat.column_ingestion.intervals import RelativeAge
from macrostrat.column_ingestion.units import Unit

#: Both ends of the timescale the model matches against, so "left geological time" is
#: checked against something real rather than against a guessed bound.
OLDEST_MA = 4031
YOUNGEST_MA = 0


def surface(position, relative_age=None):
    return AgeModelSurface(
        position=position,
        units=[Unit()],
        boundary_status=(
            BoundaryStatus.IMPOSED if relative_age else BoundaryStatus.MODELED
        ),
        relative_age=relative_age,
        # These constraints belong to the model rather than to any single unit.
        infer_relative_age=False,
    )


def test_the_model_does_not_extrapolate_past_its_constraints(test_db):
    """A near-vertical constraint pair used to put surfaces outside geological time.

    Natural boundary conditions extend the end segments indefinitely, so two constraints
    close in position and far apart in age define a slope that leaves the timescale within
    a few hundred metres. This is real GBDB input: a formation bracketed 2500-0 Ma across a
    0.1 m unit, in a section 14.8 km thick. Extrapolating it to the section base gave an
    age of 371,002,500 Ma, and above the top it went negative — which surfaced as
    `AssertionError: No interval found for age -625000.0`.

    Clamping the evaluation position to the constrained span gives constant extension
    instead: a surface outside the span takes the nearest constraint's age. That asserts
    less than an extrapolated number does, and cannot be more wrong than what it replaces.
    """
    old = RelativeAge.from_absolute(test_db, 2500.0)
    young = RelativeAge.from_absolute(test_db, 0.5)

    model = AgeModel(
        test_db,
        [
            surface(0.0),
            surface(14840.0, old),
            surface(14840.1, young),
            surface(20000.0),
        ],
    )

    # Below the lowest constraint, and above the highest.
    assert float(model._model_age(0.0)) == old.model_age()
    assert float(model._model_age(20000.0)) == young.model_age()
    # Between them the interpolation is untouched.
    assert young.model_age() < float(model._model_age(14840.05)) < old.model_age()

    # And the whole model stays inside the timescale, which is what the assertion that
    # used to fire was really checking.
    for s in model.apply():
        assert YOUNGEST_MA <= s.relative_age.model_age() <= OLDEST_MA


def test_ages_stay_monotonic_across_a_clamped_span(test_db):
    """Constant extension keeps the invariant that matters: no age inversion."""
    model = AgeModel(
        test_db,
        [
            surface(0.0),
            surface(100.0, RelativeAge.from_absolute(test_db, 500.0)),
            surface(200.0, RelativeAge.from_absolute(test_db, 400.0)),
            surface(300.0),
        ],
    )

    ages = [
        s.relative_age.model_age()
        for s in sorted(model.apply(), key=lambda s: s.position)
    ]
    assert ages == sorted(ages, reverse=True), ages
