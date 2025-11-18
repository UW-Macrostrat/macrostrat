"""
Match stratigraphic names to Macrostrat columns.

The tests are not unit tests, as they require actual data to be loaded into
Macrostrat's database.
"""

from pydantic import BaseModel
from pytest import mark

from . import get_matched_unit, standardize_names
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


@mark.parametrize("case", cases)
def test_match_strat_name(db, case):

    col_id = get_column_for_xy(db, case.xy)
    assert col_id == case.col_id
    names = standardize_names(case.match_text)
    with db.engine.connect() as conn:
        unit = get_matched_unit(conn, col_id, names)
    assert unit is not None
    assert unit.unit_id == case.unit_id
    assert unit.strat_name_id == case.strat_name_id


@mark.parametrize("case", cases)
def test_strat_name_coerce_to_pydantic(db, case):
    col_id = get_column_for_xy(db, case.xy)
    assert col_id == case.col_id
    names = standardize_names(case.match_text)
    with db.engine.connect() as conn:
        unit = get_matched_unit(conn, col_id, names)
    assert unit is not None
    result = MatchResult.from_row(unit)
    assert result.unit_id == case.unit_id
    assert result.strat_name_id == case.strat_name_id


def get_column_for_xy(db, xy):
    cols = db.run_query(
        "SELECT col_id FROM macrostrat.col_areas ca WHERE ST_Contains(ca.col_area, ST_SetSRID(ST_MakePoint(:x, :y), 4326))",
        dict(x=xy[0], y=xy[1]),
    ).all()
    if len(cols) == 0:
        raise ValueError("No column found for given coordinates")
    if len(cols) > 1:
        raise ValueError(
            "Multiple columns found for the given coordinates. This isn't handled yet."
        )
    return cols[0].col_id
