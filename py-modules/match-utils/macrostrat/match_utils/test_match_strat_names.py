"""
Match stratigraphic names to Macrostrat columns.

The tests are not unit tests, as they require actual data to be loaded into
Macrostrat's database.
"""

from pydantic import BaseModel
from pytest import mark

from . import (
    get_matched_unit,
    standardize_names,
    get_columns_for_location,
    ensure_single,
    get_column_units,
    get_all_matched_units,
)
from .models import MatchResult


# xy == -109.905/35.951
# strat name candidate Navajo
# expected match Navajo Sandstone, unit_id 14999, col_id 490, strat_name_id 3361

# same location
# strat name Halgaito Member
# expected match Halgaito Member of the Cutler Formation, unit_id 15021, col_id 490, strat_name_id 7036


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
    # Check that there is a single project_id in the data frame
    units_with_column = units.loc[~units["col_id"].isna()]
    project_ids = set(unit.project_id for i, unit in units_with_column.iterrows())
    assert len(project_ids) == 1


@mark.parametrize("case", cases)
def test_match_strat_name(db, case):

    col = ensure_single(get_columns_for_location(db, case.xy))
    assert col.col_id == case.col_id
    names = standardize_names(case.match_text)
    with db.engine.connect() as conn:
        unit = get_matched_unit(conn, col.col_id, names)
    assert unit is not None
    assert unit.unit_id == case.unit_id
    assert unit.strat_name_id == case.strat_name_id


@mark.parametrize("case", cases)
def test_strat_name_coerce_to_pydantic(db, case):
    col = ensure_single(get_columns_for_location(db, case.xy))
    assert col.col_id == case.col_id
    names = standardize_names(case.match_text)
    with db.engine.connect() as conn:
        unit = get_matched_unit(conn, col.col_id, names)
    assert unit is not None
    result = MatchResult.from_row(unit)
    assert result.unit_id == case.unit_id
    assert result.strat_name_id == case.strat_name_id


def test_match_count(db):

    names = standardize_names("Brady Butte Pluton")
    with db.engine.connect() as conn:
        units = get_all_matched_units(conn, 490, names)
    assert len(units) == 2
    assert units[0].strat_name == "Brady Butte Granodiorite"
    unit_ids = set(unit.unit_id for unit in units)
    assert unit_ids == {1852}
