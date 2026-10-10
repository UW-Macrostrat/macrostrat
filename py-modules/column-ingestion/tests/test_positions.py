"""Positions, filling and covered units, as the format's full specification defines them.

Each test names the rule it pins down; the specification is
`submodules/column-ingestion/Full specification.md`.
"""

import re
from io import StringIO
from pathlib import Path

import polars as pl
import pytest

from macrostrat.column_ingestion import notices
from macrostrat.column_ingestion.columns import get_sections_from_df
from macrostrat.column_ingestion.columns.parse import UNIT_FIELD_ALIASES
from macrostrat.column_ingestion.metadata import parse_col_type, parse_fill_values
from macrostrat.column_ingestion.units import PositionAxisType
from macrostrat.column_ingestion.units.parse import FILLED_FIELDS

HEIGHT = PositionAxisType.HEIGHT
DEPTH = PositionAxisType.DEPTH
ORDINAL = PositionAxisType.ORDINAL

SPEC = (
    Path(__file__).parents[3]
    / "submodules"
    / "column-ingestion"
    / "Full specification.md"
)


def sheet(text: str) -> pl.DataFrame:
    # Every cell as text, as a spreadsheet would arrive
    return pl.read_csv(StringIO(text.strip()), separator="|", infer_schema_length=0)


def parse(db, text: str, **kwargs):
    with notices.collect_notices() as collected:
        sections = get_sections_from_df(db, sheet(text), **kwargs)
    units = sorted(
        (u for s in sections["1"] for u in s.units),
        key=lambda u: min(u.b_pos, u.t_pos),
    )
    return units, [n.code for n in collected]


def liths(unit) -> set[str]:
    return {lith.name for lith in unit.lithology}


def test_height_section_top_first_with_closing_row(test_db):
    """One position per row; the empty row at the top closes the section."""
    units, codes = parse(
        test_db,
        """
col_id|position|lithology|strat_name
1|9.7||
1|8.3|sandstone|
1|6.9|conglomerate|
1|0|sandstone|Wood Canyon Formation
""",
        fill_values=True,
    )
    assert [(u.b_pos, u.t_pos) for u in units] == [(0, 6.9), (6.9, 8.3), (8.3, 9.7)]
    # Filling runs up the section from the base
    assert [u.name for u in units] == ["Wood Canyon Formation"] * 3
    # An empty closing row is expected, so nothing is reported
    assert codes == []


def test_depth_core_reads_downward(test_db):
    """On a depth axis a row's position is its unit's top, and values fill down."""
    units, codes = parse(
        test_db,
        """
col_id|depth|lithology|strat_name
1|0|mudstone|Upper unit
1|3.2|limestone|
1|7.5||
""",
        position=DEPTH,
        fill_values=True,
    )
    assert [(u.t_pos, u.b_pos) for u in units] == [(0, 3.2), (3.2, 7.5)]
    assert [u.name for u in units] == ["Upper unit", "Upper unit"]
    assert [u.outcrop for u in units] == ["subsurface", "subsurface"]
    assert codes == []


def test_tops_only(test_db):
    """Only one bound is needed; a missing base comes from the top of the unit below."""
    units, _ = parse(
        test_db,
        """
col_id|t_pos|lithology
1|0|
1|5|shale
1|12|sandstone
""",
    )
    assert [(u.b_pos, u.t_pos) for u in units] == [(0, 5), (5, 12)]


def test_none_ends_a_run_and_spaces_are_blank(test_db):
    units, _ = parse(
        test_db,
        """
col_id|position|strat_name
1|0|Lower Formation
1|1|
1|2|NONE
1|3|
1|4|Upper Formation
1|5|
1|6|
""",
        fill_values=True,
    )
    assert [u.name for u in units] == [
        "Lower Formation",
        "Lower Formation",
        None,
        None,
        "Upper Formation",
        "Upper Formation",
    ]


def test_no_filling_unless_asked(test_db):
    units, _ = parse(
        test_db,
        """
col_id|position|strat_name
1|0|Lower Formation
1|1|
1|2|none
1|3|
""",
    )
    assert [u.name for u in units] == ["Lower Formation", None, None]


def test_age_axis_slots(test_db):
    """A unit at n spans n to n + 1; a skipped number is a gap, not a longer unit."""
    units, codes = parse(
        test_db,
        """
col_id|position|strat_name|b_int|b_prop
1|1|Oldest|Cambrian|0
1|2||Cambrian|0.5
1|4|Youngest|Ordovician|0
""",
        position=ORDINAL,
        fill_values=True,
    )
    assert [(u.b_pos, u.t_pos) for u in units] == [(1, 2), (2, 3), (4, 5)]
    # The top of 1 is the base of 2; nothing meets the base of 4
    assert units[0].t_age.proportion == 0.5
    assert units[1].t_age is None
    # No filling on an age axis
    assert units[1].name is None
    assert "no-filling-on-age-axis" in codes


def test_lateral_equivalents_share_a_surface(test_db):
    """Units sharing a base both extend to the next surface."""
    units, _ = parse(
        test_db,
        """
col_id|position|strat_name
1|0|East member
1|0|West member
1|10|
""",
    )
    assert sorted((u.name, u.b_pos, u.t_pos) for u in units) == [
        ("East member", 0, 10),
        ("West member", 0, 10),
    ]


def test_closing_row_dates_the_top(test_db):
    """A b_int on the closing row is the age of the column's top surface."""
    units, _ = parse(
        test_db,
        """
col_id|position|strat_name|b_int|b_prop
1|20||Ordovician|
1|0|Only unit|Cambrian|0.2
""",
    )
    [unit] = units
    assert unit.t_age.interval.name == "Ordovician"
    # A blank b_prop is the interval's oldest end, wherever its age is carried
    assert unit.t_age.proportion == 0


def test_carried_age_keeps_its_proportion(test_db):
    """The surface between two units has one age, read from the unit above's base."""
    units, _ = parse(
        test_db,
        """
col_id|position|strat_name|b_int
1|0|Lower|Cambrian
1|10|Upper|Ordovician
1|20|
""",
    )
    assert units[0].t_age.interval.name == "Ordovician"
    assert units[0].t_age.proportion == units[1].b_age.proportion == 0


def test_closing_row_values_are_reported(test_db):
    _, codes = parse(
        test_db,
        """
col_id|position|lithology
1|0|shale
1|10|sandstone
""",
    )
    assert "closing-row-values-ignored" in codes


def test_covered_units(test_db):
    units, codes = parse(
        test_db,
        """
col_id|position|lithology|covered
1|0|sandstone|
1|5|shale|y
1|8||
""",
    )
    assert [u.outcrop for u in units] == ["surface", "covered"]
    # The inferred lithology is kept
    assert liths(units[1]) == {"shale"}
    assert codes == []


def test_covered_on_a_depth_axis_warns(test_db):
    _, codes = parse(
        test_db,
        """
col_id|position|covered
1|0|y
1|4|
""",
        position=DEPTH,
    )
    assert "covered-on-depth-axis" in codes


def test_covered_by_name(test_db):
    """A unit named `covered` is a covered unit; filling carries on past it."""
    units, _ = parse(
        test_db,
        """
col_id|position|unit_name|lithology|strat_name
1|0||sandstone|Wood Canyon Formation
1|4|covered||
1|6|||
1|9|||
""",
        fill_values=True,
    )
    assert [u.outcrop for u in units] == ["surface", "covered", "surface"]
    assert [u.name for u in units] == ["Wood Canyon Formation"] * 3
    assert [liths(u) for u in units] == [{"sandstone"}] * 3


def test_covered_by_lithology(test_db):
    """`covered` in place of a lithology leaves the unit's lithology unknown."""
    units, _ = parse(
        test_db,
        """
col_id|position|lithology
1|0|sandstone
1|4|Covered
1|6|
1|9|
""",
        fill_values=True,
    )
    assert [u.outcrop for u in units] == ["surface", "covered", "surface"]
    assert [liths(u) for u in units] == [{"sandstone"}, set(), {"sandstone"}]


def test_gap_row(test_db):
    """A row named `gap` ends the unit below it, and no unit fills the gap."""
    units, codes = parse(
        test_db,
        """
col_id|position|unit_name|strat_name
1|12||
1|8||
1|5|gap|
1|0||Lower Formation
""",
        fill_values=True,
    )
    assert [(u.b_pos, u.t_pos) for u in units] == [(0, 5), (8, 12)]
    assert [u.name for u in units] == ["Lower Formation"] * 2
    assert codes == []


def test_explicit_bound_headers(test_db):
    units, _ = parse(
        test_db,
        """
col_id|base|top|strat_name
1|0|4|Lower
1|6|9|Upper
""",
    )
    # Explicit bounds keep the gap between 4 and 6
    assert [(u.b_pos, u.t_pos) for u in units] == [(0, 4), (6, 9)]


def test_axis_named_header_on_the_wrong_axis(test_db):
    _, codes = parse(
        test_db,
        """
col_id|depth|strat_name
1|0|Unit
1|5|
""",
        position=HEIGHT,
    )
    assert "axis-name-mismatch" in codes


def test_per_column_axis(test_db):
    """A column's own axis overrides the workbook default."""
    with notices.collect_notices():
        sections = get_sections_from_df(
            test_db,
            sheet(
                """
col_id|position|strat_name
1|0|Top unit
1|5|
"""
            ),
            column_settings={"1": (DEPTH, False)},
        )
    [unit] = sections["1"][0].units
    assert (unit.t_pos, unit.b_pos) == (0, 5)


@pytest.mark.parametrize(
    "value,expected,warns",
    [
        ("y", True, False),
        ("TRUE", True, False),
        ("n", False, False),
        (None, None, False),
        ("up", False, True),
    ],
)
def test_fill_values_setting(value, expected, warns):
    with notices.collect_notices() as collected:
        assert parse_fill_values(value) is expected
    assert bool(collected.warnings) is warns


# The specification and this module must say the same thing


def _spec_list_items(section: str) -> dict[str, list[str]]:
    """`- `name`: `a`, `b`` list items in one `## ` section, keyed by name."""
    text = SPEC.read_text()
    body = text.split(f"## {section}", 1)[1].split("\n## ", 1)[0]
    items, current = {}, None
    for line in body.splitlines():
        match = re.match(r"- `(\w+)`\s*:(.*)", line)
        if match:
            current = match.group(1)
            items[current] = re.findall(r"`(\w+)`", match.group(2))
        elif current and line.startswith("  "):
            items[current] += re.findall(r"`(\w+)`", line)
        else:
            current = None
    return items


@pytest.mark.skipif(
    not SPEC.exists(), reason="column-ingestion submodule not checked out"
)
def test_position_aliases_match_the_specification():
    documented = _spec_list_items("Field aliases")
    for target in ("position", "b_pos", "t_pos"):
        implemented = {k for k, v in UNIT_FIELD_ALIASES.items() if v == target}
        assert implemented == set(documented[target]), target


@pytest.mark.skipif(
    not SPEC.exists(), reason="column-ingestion submodule not checked out"
)
def test_filled_fields_match_the_specification():
    text = SPEC.read_text()
    listed = text.split("- Filled fields:", 1)[1].split("\n- ", 1)[0]
    documented = {
        "name" if f == "unit_name" else f for f in re.findall(r"`(\w+)`", listed)
    }
    assert documented == set(FILLED_FIELDS)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("measured", "section"),
        ("Composite", "column"),
        ("section", "section"),
        ("column", "column"),
        (None, None),
    ],
)
def test_col_type_names(value, expected):
    assert parse_col_type(value) == expected


def test_unknown_col_type_warns():
    with notices.collect_notices() as collected:
        assert parse_col_type("borehole") is None
    assert [n.code for n in collected] == ["unknown-column-type"]


def test_a_traverse_line_is_a_specific_location():
    from macrostrat.column_ingestion.columns.parse import Column
    from macrostrat.column_ingestion.validation import validate_column

    codes = {}
    for geom in (
        "LINESTRING(16 -24, 16.1 -24.1)",
        "POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))",
    ):
        col = Column(local_id="A", name="A", col_type="section", geom=geom)
        with notices.collect_notices() as collected:
            validate_column(col)
        codes[geom.split("(")[0]] = {n.code for n in collected}
    assert "no-specific-location" not in codes["LINESTRING"]
    assert "no-specific-location" in codes["POLYGON"]
