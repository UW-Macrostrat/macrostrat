"""Tests for the units natural key and the shared reconciliation planner.

Pure — no database needed.
"""

from macrostrat.column_ingestion.intervals import UNMODELED_INTERVAL
from macrostrat.column_ingestion.reconciliation import plan_reconciliation
from macrostrat.column_ingestion.units import UNIT_COLUMNS, unit_identity
from macrostrat.column_ingestion.units.writer import _desired_unit_row


def existing(id, *, name="A", pb=10.0, pt=0.0, fo=100, lo=100, **kwargs):
    row = {
        "id": id,
        "col_id": 1,
        "section_id": 2,
        "strat_name": name,
        "position_bottom": pb,
        "position_top": pt,
        "max_thick": 10.0,
        "min_thick": 10.0,
        "outcrop": "surface",
        "color": "",
        "fo": fo,
        "lo": lo,
    }
    row.update(kwargs)
    return row


def desired(*, name="A", pb=10.0, pt=0.0, fo=100, lo=100, **kwargs):
    row = existing(None, name=name, pb=pb, pt=pt, fo=fo, lo=lo)
    row.pop("id")
    row.update(kwargs)
    return row


def plan(existing_rows, desired_rows):
    return plan_reconciliation(
        existing_rows,
        desired_rows,
        key=unit_identity,
        owned_columns=UNIT_COLUMNS,
        scales={"max_thick": 2, "min_thick": 2},
    )


def test_unchanged_section_is_a_noop():
    rows = [existing(1), existing(2, name="B", pb=20.0, pt=10.0)]
    want = [desired(), desired(name="B", pb=20.0, pt=10.0)]

    assert plan(rows, want).is_noop


def test_position_key_matches_across_float_noise():
    """Positions are `numeric(7,3)` and part of the key. A rebuilt value differing in
    the ninth decimal is the same stored position and must match, not replace."""
    rows = [existing(1, pb=10.0, pt=0.0)]
    want = [desired(pb=10.000000000001, pt=0.0)]

    result = plan(rows, want)

    assert result.is_noop, "float noise must not orphan the existing unit"
    assert result.unchanged == [1]


def test_identity_ignores_strat_name_whitespace():
    rows = [existing(1, name="Mazko Formation")]
    want = [desired(name="  Mazko Formation  ")]

    assert plan(rows, want).is_noop


def test_existing_fo_lo_are_never_overwritten():
    """For eODP columns `fo`/`lo` *are* the age control, and this writer cannot tell
    whether it is looking at such a column. So a matched row keeps whatever it has: the
    key ignores them and they are not owned columns."""
    rows = [existing(7, fo=489, lo=490)]
    want = [desired(fo=1, lo=1)]  # what a generic re-import would otherwise assert

    result = plan(rows, want)

    assert result.is_noop, "differing fo/lo must not even register as a change"
    assert result.unchanged == [7]
    assert "fo" not in UNIT_COLUMNS and "lo" not in UNIT_COLUMNS


def test_key_excludes_fo_and_lo():
    """Regression: including fo/lo in the key would make a corrected interval look like
    a different unit, orphaning the original."""
    a = unit_identity(existing(1, fo=1, lo=1))
    b = unit_identity(existing(1, fo=489, lo=490))
    assert a == b


def test_new_and_removed_units():
    rows = [existing(1), existing(2, name="B", pb=20.0, pt=10.0)]
    want = [desired(), desired(name="C", pb=30.0, pt=20.0)]

    result = plan(rows, want)

    assert result.unchanged == [1]
    assert result.deletes == [2]
    assert len(result.inserts) == 1


def test_surplus_duplicates_are_cleaned_up():
    """25 of the 34 colliding key groups in the corpus are exact-duplicate rows."""
    rows = [existing(1), existing(2), existing(3)]
    want = [desired()]

    result = plan(rows, want)

    assert result.unchanged == [1]
    assert result.deletes == [2, 3]


class FakeUnit:
    """Minimal stand-in: a unit that carries no interval assignment."""

    def __init__(self, name, *, interval=None):
        self.name = name
        self.b_age = interval
        self.t_age = interval
        self.id = -1
        self.col_id = 1
        self.section_id = 2
        self.b_pos = 10.0
        self.t_pos = 0.0


def test_units_without_intervals_get_the_unmodeled_sentinel():
    """Ingesting the physical column is decoupled from age modeling, and units with no
    interval are normal for high-resolution stratigraphy. `fo`/`lo` are NOT NULL, so a
    new row takes an unmistakable placeholder rather than a plausible-looking age."""
    row = _desired_unit_row(FakeUnit("A"))

    assert row["fo"] == row["lo"] == UNMODELED_INTERVAL


def test_unmodeled_sentinel_spans_all_of_geologic_time():
    """499 is Precambrian-Phanerozoic (4031-0 Ma) — a non-answer, not a wrong answer.
    Guards against it drifting to something that reads as a real interval."""
    assert UNMODELED_INTERVAL == 499
