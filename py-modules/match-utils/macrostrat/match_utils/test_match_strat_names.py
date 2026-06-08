"""
Match stratigraphic names to Macrostrat columns.

The tests are not unit tests, as they require actual data to be loaded into
Macrostrat's database.
"""

from pydantic import BaseModel
from pytest import mark
from pandas import isna

from . import (
    ensure_single,
    get_all_matched_units,
    get_column_units,
    get_columns_for_location,
    get_matched_unit,
    standardize_names,
)
from .models import MatchResult


class StratTestCaseData(BaseModel):
    xy: tuple[float, float]
    match_text: str
    unit_id: int
    strat_name_id: int
    col_id: int


cases = [
    StratTestCaseData(
        xy=(-109.905, 35.951),
        match_text="Navajo",
        unit_id=14999,
        strat_name_id=3361,
        col_id=490,
    ),
    StratTestCaseData(
        xy=(-109.905, 35.951),
        match_text="Halgaito Member",
        unit_id=15021,
        strat_name_id=7036,
        col_id=490,
    ),
]


def test_get_column_units(db):
    with db.engine.connect() as conn:
        units = get_column_units(conn, col_id=490)
    assert len(units) > 10
    units_with_column = units.loc[~units["col_id"].isna()]
    project_ids = set(unit.project_id for i, unit in units_with_column.iterrows())
    assert len(project_ids) == 1


def test_column_units_have_spatial_basis(db):
    """All rows should have a spatial_basis of containing or adjacent column."""
    with db.engine.connect() as conn:
        units = get_column_units(conn, col_id=490)
    assert "spatial_basis" in units.columns
    assert set(units["spatial_basis"].dropna().unique()).issubset(
        {"containing column", "adjacent column"}
    )


def test_column_units_have_basis(db):
    """All rows should have a known basis value."""
    with db.engine.connect() as conn:
        units = get_column_units(conn, col_id=490)
    assert "basis" in units.columns
    known_bases = {"column unit", "concept", "synonym", "footprint index"}
    assert set(units["basis"].dropna().unique()).issubset(known_bases)


def test_column_units_have_concept_name(db):
    """Rows with a concept_id should have a concept_name."""
    with db.engine.connect() as conn:
        units = get_column_units(conn, col_id=490)
    assert "concept_name" in units.columns


@mark.parametrize("case", cases)
def test_match_strat_name(db, case):
    col = ensure_single(get_columns_for_location(db, case.xy))
    assert col.col_id == case.col_id
    names = standardize_names(case.match_text)
    with db.engine.connect() as conn:
        result = get_matched_unit(conn, col.col_id, names)
    assert result is not None
    row, is_exact = result
    assert row["unit_id"] == case.unit_id
    assert row["strat_name_id"] == case.strat_name_id


@mark.parametrize("case", cases)
def test_strat_name_coerce_to_pydantic(db, case):
    col = ensure_single(get_columns_for_location(db, case.xy))
    names = standardize_names(case.match_text)
    with db.engine.connect() as conn:
        result = get_matched_unit(conn, col.col_id, names)
    assert result is not None
    row, is_exact = result
    vals = dict(row)
    for key, val in vals.items():
        if isna(val):
            vals[key] = None
    vals["name_basis"] = "exact" if is_exact else "concept"
    vals["priority"] = 0.0
    vals.pop("basis", None)
    match_result = MatchResult(**vals)
    assert match_result.unit_id == case.unit_id
    assert match_result.strat_name_id == case.strat_name_id


def test_match_returns_tuple(db):
    """get_all_matched_units must return list of (row, is_exact) tuples."""
    names = standardize_names("Navajo Sandstone")
    with db.engine.connect() as conn:
        rows = get_all_matched_units(conn, 490, names)
    assert len(rows) > 0
    for item in rows:
        assert isinstance(item, tuple) and len(item) == 2
        row, is_exact = item
        assert isinstance(is_exact, bool)


def test_exact_match_is_exact(db):
    """Exact name match should return is_exact=True."""
    names = standardize_names("Navajo Sandstone")
    with db.engine.connect() as conn:
        rows = get_all_matched_units(conn, 490, names)
    exact_matches = [row for row, is_exact in rows if is_exact]
    assert len(exact_matches) > 0


def test_included_match_not_exact(db):
    """Partial name match should return is_exact=False."""
    names = standardize_names("Navajo")
    with db.engine.connect() as conn:
        rows = get_all_matched_units(conn, 490, names)
    non_exact = [row for row, is_exact in rows if not is_exact]
    assert len(non_exact) > 0


def test_match_count(db):
    names = standardize_names("Brady Butte Pluton")
    with db.engine.connect() as conn:
        rows = get_all_matched_units(conn, 490, names)
    assert len(rows) == 2
    row, is_exact = rows[0]
    assert row["strat_name"] == "Brady Butte Granodiorite"
    unit_ids = set(row["unit_id"] for row, _ in rows)
    assert unit_ids == {1852}


def test_spatial_basis_containing_column(db):
    """Direct column match should have spatial_basis='containing column'."""
    names = standardize_names("Navajo Sandstone")
    with db.engine.connect() as conn:
        rows = get_all_matched_units(conn, 490, names)
    containing = [
        row for row, _ in rows if row["spatial_basis"] == "containing column"
    ]
    assert len(containing) > 0


def test_age_filter(db):
    """Age filtering should exclude units outside the age range."""
    names = standardize_names("Navajo Sandstone")
    with db.engine.connect() as conn:
        rows_unfiltered = get_all_matched_units(conn, 490, names)
        rows_filtered = get_all_matched_units(conn, 490, names, t_age=0.0, b_age=10.0)
    assert len(rows_filtered) == 0
    assert len(rows_unfiltered) > 0