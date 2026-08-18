"""Tests for matching a rebuilt age model onto existing `unit_boundaries` rows.

The planner is pure, so these need no database.
"""

from macrostrat.column_ingestion.age_model.reconciliation import (
    AGE_MODEL_COLUMNS,
    plan_boundary_reconciliation,
)


def existing(id, unit_id, unit_id_2, **kwargs):
    row = {
        "id": id,
        "unit_id": unit_id,
        "unit_id_2": unit_id_2,
        "t1": 489,
        "t1_prop": 0.5,
        "t1_age": 4.4665,
        "boundary_status": "modeled",
        "boundary_position": 10.0,
    }
    row.update(kwargs)
    return row


def desired(unit_id, unit_id_2, **kwargs):
    row = {
        "unit_id": unit_id,
        "unit_id_2": unit_id_2,
        "t1": 489,
        "t1_prop": 0.5,
        "t1_age": 4.4665,
        "boundary_status": "modeled",
        "boundary_position": 10.0,
        "section_id": 13768,
    }
    row.update(kwargs)
    return row


def test_unchanged_model_is_a_noop():
    """The point of the exercise: rebuilding an unchanged section touches nothing."""
    rows = [existing(1, 100, None), existing(2, 101, 100), existing(3, None, 101)]
    want = [desired(100, None), desired(101, 100), desired(None, 101)]

    plan = plan_boundary_reconciliation(rows, want)

    assert plan.is_noop
    assert plan.unchanged == [1, 2, 3]


def test_legacy_zero_sentinel_matches_our_null():
    """Legacy rows use 0 for "no unit"; we write None. Same surface, so the row
    must be matched rather than replaced."""
    rows = [existing(1, 100, 0), existing(2, 0, 100)]
    want = [desired(100, None), desired(None, 100)]

    plan = plan_boundary_reconciliation(rows, want)

    assert plan.is_noop, "0 and NULL should not be treated as different surfaces"
    assert sorted(plan.unchanged) == [1, 2]


def test_moved_age_updates_in_place():
    rows = [existing(7, 101, 100, t1_age=4.4665)]
    want = [desired(101, 100, t1_age=5.1234)]

    plan = plan_boundary_reconciliation(rows, want)

    assert plan.inserts == [] and plan.deletes == []
    assert len(plan.updates) == 1
    boundary_id, values = plan.updates[0]
    assert boundary_id == 7, "identity must be preserved across an age change"
    assert values["t1_age"] == 5.1234
    assert set(values) == set(AGE_MODEL_COLUMNS), "only age-model columns are written"


def test_curated_columns_are_never_written():
    """`paleo_lat` and friends are not the age model's to touch."""
    rows = [existing(7, 101, 100, paleo_lat=12.5, paleo_lng=-40.0, ref_id=99)]
    want = [desired(101, 100, t1_age=9.0)]

    _, values = plan_boundary_reconciliation(rows, want).updates[0]

    for column in ("paleo_lat", "paleo_lng", "ref_id", "boundary_type"):
        assert column not in values


def test_float_noise_below_column_precision_is_not_a_change():
    """`t1_prop` is numeric(6,5). A rebuilt value differing in the 9th decimal is
    the same stored value, and must not count as an update."""
    rows = [existing(1, 101, 100, t1_prop=0.66036)]
    want = [desired(101, 100, t1_prop=0.6603600000001)]

    assert plan_boundary_reconciliation(rows, want).is_noop


def test_new_surfaces_insert_and_vanished_ones_delete():
    """Units added at the base of a hole — the Site 960 Hole A case."""
    rows = [existing(1, 100, None), existing(2, 101, 100), existing(3, None, 101)]
    want = [
        desired(100, None),
        desired(101, 100),
        desired(102, 101),  # new unit below
        desired(None, 102),
    ]

    plan = plan_boundary_reconciliation(rows, want)

    assert sorted(plan.unchanged) == [1, 2]
    assert plan.deletes == [3], "the old basal boundary no longer separates 101/None"
    assert len(plan.inserts) == 2


def test_surplus_duplicate_rows_are_deleted():
    """The database has 255 groups of exact-duplicate rows sharing a natural key.
    One is matched and the rest are cleaned up."""
    rows = [existing(1, 101, 100), existing(2, 101, 100), existing(3, 101, 100)]
    want = [desired(101, 100)]

    plan = plan_boundary_reconciliation(rows, want)

    assert plan.unchanged == [1]
    assert plan.deletes == [2, 3]


def test_empty_model_deletes_everything():
    rows = [existing(1, 100, None), existing(2, None, 100)]

    plan = plan_boundary_reconciliation(rows, [])

    assert plan.deletes == [1, 2]
    assert not plan.updates and not plan.inserts


def test_first_build_inserts_everything():
    want = [desired(100, None), desired(None, 100)]

    plan = plan_boundary_reconciliation([], want)

    assert len(plan.inserts) == 2
    assert not plan.updates and not plan.deletes


def test_matched_legacy_row_keeps_its_zero_sentinel():
    """We write NULL going forward but do not rewrite the legacy 0s in place —
    migrating them wholesale is a separate, deferred decision. So `unit_id` and
    `unit_id_2` must never appear in an update."""
    rows = [existing(1, 100, 0), existing(2, 0, 100)]
    want = [desired(100, None, t1_age=9.0), desired(None, 100, t1_age=9.0)]

    plan = plan_boundary_reconciliation(rows, want)

    assert not plan.inserts and not plan.deletes
    assert [i for i, _ in plan.updates] == [1, 2], "rows matched, not replaced"
    for _, values in plan.updates:
        assert "unit_id" not in values and "unit_id_2" not in values


def test_new_boundaries_are_written_with_null_not_zero():
    """Inserts come straight from UnitBoundary.to_dict(), which uses None."""
    plan = plan_boundary_reconciliation([], [desired(100, None), desired(None, 100)])

    sentinels = [(row["unit_id"], row["unit_id_2"]) for row in plan.inserts]
    assert sentinels == [(100, None), (None, 100)]
    assert not any(0 in pair for pair in sentinels)
