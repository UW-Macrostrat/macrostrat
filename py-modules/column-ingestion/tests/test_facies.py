"""The facies sheet: a unit's own descriptions win; its facies fill what it leaves blank."""

from io import StringIO

import polars as pl

from macrostrat.column_ingestion import notices
from macrostrat.column_ingestion.columns import get_sections_from_df
from macrostrat.column_ingestion.facies import facies_from_df, parse_facies_refs
from macrostrat.column_ingestion.vocabulary import Vocabulary

FACIES = """
facies_id|lithology|environment|description
F1|sandstone (50%); shale|shoreface|Rippled sandstone and shale
F2|lime mudstone|peritidal|Mud-cracked lime mudstone
"""


def sheet(text: str) -> pl.DataFrame:
    return pl.read_csv(StringIO(text.strip()), separator="|", infer_schema_length=0)


def parse_units(db, units: str):
    vocab = Vocabulary(db)
    with notices.collect_notices() as collected:
        vocab.facies = facies_from_df(sheet(FACIES), vocab)
        sections = get_sections_from_df(db, sheet(units), vocab=vocab)
    units = sorted((u for s in sections["1"] for u in s.units), key=lambda u: u.b_pos)
    return units, [n.code for n in collected]


def names(items) -> set[str]:
    return {item.name for item in items}


def test_parse_facies_refs():
    assert parse_facies_refs("F1 (60%); F2, F3 (0.25)") == [
        ("F1", 0.6),
        ("F2", None),
        ("F3", 0.25),
    ]
    assert parse_facies_refs(None) == []


def test_facies_fill_what_the_unit_leaves_blank(test_db):
    units, codes = parse_units(
        test_db,
        """
col_id|position|lithology|facies
1|0||F1
1|5|dolomite|F2
1|9||
""",
    )
    # No lithology of its own: the facies' lithologies and environment
    assert names(units[0].lithology) == {"sandstone", "shale"}
    assert names(units[0].environment) == {"shoreface"}
    # Its own lithology wins; the facies still supplies the environment
    assert names(units[1].lithology) == {"dolomite"}
    assert names(units[1].environment) == {"peritidal"}
    assert codes == []


def test_facies_proportion_scales_lithologies(test_db):
    units, _ = parse_units(
        test_db,
        """
col_id|position|facies
1|0|F1 (50%); F2
1|9|
""",
    )
    props = {lith.name: lith.prop for lith in units[0].lithology}
    assert names(units[0].lithology) == {"sandstone", "shale", "lime mudstone"}
    assert names(units[0].environment) == {"shoreface", "peritidal"}
    # Half of a facies that is half sandstone
    assert props["sandstone"] == 0.25


def test_unknown_facies_warns(test_db):
    _, codes = parse_units(
        test_db,
        """
col_id|position|facies
1|0|F9
1|9|
""",
    )
    assert codes == ["unknown-facies"]
