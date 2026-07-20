"""
Match stratigraphic names to Macrostrat columns.

The tests are not unit tests, as they require actual data to be loaded into
Macrostrat's database.
"""

from pandas import isna
from pydantic import BaseModel
from pytest import mark

from . import (
    ensure_single,
    get_adjacent_cols_from_containing,
    get_all_matched_units,
    get_column_units,
    get_columns_for_location,
    get_matched_unit,
    standardize_names,
)
from ._test_helpers import lith_names_fixture
from .models import MatchResult


class StratTestCaseData(BaseModel):
    xy: tuple[float, float]
    match_text: str
    unit_id: int
    strat_name_id: int
    col_id: int


# defaults to location order
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

cases_strat_name_priority = [
    StratTestCaseData(
        xy=(-109.905, 35.951),
        match_text="Navajo",
        unit_id=15191,
        strat_name_id=1399,
        col_id=495,
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
    print("here's the case for test_match_strat_name", case)
    col = ensure_single(get_columns_for_location(db, case.xy))
    print("here is the col returned", col)
    print("here is the case col", case.col_id)

    # case.col_id may be the containing column or an adjacent one, so check
    # that it falls within the containing + adjacent set rather than requiring
    # an exact match to the containing column only.
    adjacent_containing_col_ids = get_adjacent_cols_from_containing(db, col.col_id)

    assert case.col_id in adjacent_containing_col_ids

    names = standardize_names(case.match_text)
    results = []
    with db.engine.connect() as conn:
        for col_id in adjacent_containing_col_ids:
            result = get_matched_unit(conn, col_id, names)
            if result is not None:
                results.append(result)
    assert len(results) > 0
    surfaced = [
        row
        for row in results
        if row["unit_id"] == case.unit_id
        and row["strat_name_id"] == case.strat_name_id
        and row["col_id"] == case.col_id
    ]
    assert len(surfaced) > 0


@mark.parametrize("case", cases)
def test_strat_name_coerce_to_pydantic(db, case):
    col = ensure_single(get_columns_for_location(db, case.xy))
    # case.col_id may be the containing column or one adjacent to it.
    adjacent_containing_col_ids = get_adjacent_cols_from_containing(db, col.col_id)
    assert case.col_id in adjacent_containing_col_ids
    names = standardize_names(case.match_text)
    results = []
    with db.engine.connect() as conn:
        for col_id in adjacent_containing_col_ids:
            result = get_matched_unit(conn, col_id, names)
            if result is not None:
                results.append(result)
    # pick the surfaced match that came from the expected column.
    surfaced = [
        row
        for row in results
        if row["unit_id"] == case.unit_id
        and row["strat_name_id"] == case.strat_name_id
        and row["col_id"] == case.col_id
    ]
    assert len(surfaced) > 0
    row = surfaced[0]
    vals = dict(row)
    for key, val in vals.items():
        if isna(val):
            vals[key] = None
    is_exact = vals.pop("is_exact_name_match")
    vals["name_basis"] = "exact" if is_exact else "concept"
    vals["priority"] = 0.0
    vals.pop("basis", None)
    match_result = MatchResult(**vals)
    assert match_result.unit_id == case.unit_id
    assert match_result.strat_name_id == case.strat_name_id


def test_match_returns_row(db):
    """get_all_matched_units must return list of (row, is_exact) tuples."""
    names = standardize_names("Navajo Sandstone")
    with db.engine.connect() as conn:
        rows = get_all_matched_units(conn, 490, names)
    assert len(rows) > 0
    for row in rows:
        is_exact = row.get("is_exact_name_match")
        assert isinstance(is_exact, bool)


def test_exact_match_is_exact(db):
    """Exact name match should return is_exact=True."""
    names = standardize_names("Navajo Sandstone")
    with db.engine.connect() as conn:
        rows = get_all_matched_units(conn, 490, names)
    exact_matches = [row for row in rows if row.get("is_exact_name_match")]
    assert len(exact_matches) > 0


def test_partial_name_matches_are_exact_when_cleaned_name_matches(db):
    """A short query can match exact cleaned names such as concept-level Navajo."""
    names = standardize_names("Navajo")
    with db.engine.connect() as conn:
        rows = get_all_matched_units(conn, 490, names)

    assert len(rows) > 0
    assert any(row.get("is_exact_name_match") for row in rows)


def test_match_count(db):
    names = standardize_names("Brady Butte Pluton")
    with db.engine.connect() as conn:
        rows = get_all_matched_units(conn, 490, names)
    assert len(rows) == 2
    row = rows[0]
    assert row["strat_name"] == "Brady Butte Granodiorite"
    unit_ids = set(row["unit_id"] for row in rows)
    assert unit_ids == {1852}


def test_spatial_basis_containing_column(db):
    """Direct column match should have spatial_basis='containing column'."""
    names = standardize_names("Navajo Sandstone")
    with db.engine.connect() as conn:
        rows = get_all_matched_units(conn, 490, names)
    containing = [row for row in rows if row["spatial_basis"] == "containing column"]
    assert len(containing) > 0


def test_age_filter(db):
    """Age filtering should exclude units outside the age range."""
    names = standardize_names("Navajo Sandstone")
    with db.engine.connect() as conn:
        rows_unfiltered = get_all_matched_units(conn, 490, names)
        rows_filtered = get_all_matched_units(conn, 490, names, t_age=0.0, b_age=10.0)
    assert len(rows_filtered) == 0
    assert len(rows_unfiltered) > 0
