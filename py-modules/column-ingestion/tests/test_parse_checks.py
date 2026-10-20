"""Bad workbook values reported while parsing, rather than by the database on write.

Every case here once reached PostGIS or an enum cast and failed the ingest with a
driver exception and no notice. None of these tests needs a database.
"""

import polars as pl
import pytest

from macrostrat.column_ingestion import notices
from macrostrat.column_ingestion.columns import columns_from_df
from macrostrat.column_ingestion.headers import clean_header, clean_headers
from macrostrat.column_ingestion.metadata import metadata_from_dict
from macrostrat.column_ingestion.refs import references_from_df
from macrostrat.column_ingestion.validation import validate_dataset
from macrostrat.column_ingestion.wkt import check_wkt

COMPILATION_CODES = ["", "COSUNA", "COSUNA II", "Canada", "IODP", "ODP", "DSDP"]


def parse_columns(rows: list[dict], meta: dict | None = None):
    with notices.collect_notices() as collected:
        columns = columns_from_df(pl.DataFrame(rows), metadata_from_dict(meta or {}))
        validate_dataset(columns)
    return columns, collected


def codes(collected, level=notices.Level.ERROR) -> list[str]:
    return [n.code for n in collected.at_level(level)]


# --- geometry text ----------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        "POLYGON ((15.91375 -24.484649, 16.442625 -24.484649, 16.442625 -24.026397, "
        "15.91375 -24.484649))",
        "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 0)), ((2 2, 3 2, 3 3, 2 2)))",
        "LINESTRING(16.0677 -24.25, 16.0679 -24.2471)",
        "linestring z (1 2 3, 4 5 6)",
        "MULTILINESTRING((0 0, 1 1), (2 2, 3 3))",
        "POLYGON((0 0, 1e-1 0, 1E-1 1, 0 0))",
    ],
)
def test_wkt_is_accepted(text):
    assert check_wkt(text) is None


@pytest.mark.parametrize(
    "text, expected",
    [
        ("POINT(0,0)", "separated by a space"),
        ("0", "should start with a geometry type"),
        ("53.12, -119.15", "latitude, longitude pair"),
        ("75.25 -95.78", "latitude, longitude pair"),
        ("37°19.162'N 118°10.707'W", "degrees and minutes"),
        ("37 19.162 N, 118 10.707 W", "degrees and minutes"),
        ("POINT(16 -24)", "`lat` and `lng`"),
        ("MULTIPOINT((0 0), (1 1))", "not a MULTIPOINT"),
        ("POLYGON((0 0, 1 0, 1 1, 0 1))", "must end on the point it starts from"),
        ("POLYGON((0 0, 1 1, 0 0))", "at least four points"),
        ("LINESTRING(0 0)", "at least two points"),
        ("POLYGON((0 0, 1 0, 1 1, 0 0)", "not closed"),
        ("POLYGON(0 0, 1 0, 1 1, 0 0)", "nest"),
        ("POLYGON((-119 53, -118 53, -118 54, -119 53)) junk", "after the geometry"),
        (
            "POLYGON((500000 4000000, 500100 4000000, 500100 4000100, 500000 4000000))",
            "not a longitude and latitude",
        ),
        ("POLYGON EMPTY", "empty"),
        ("CIRCLE(0 0)", "not a geometry type"),
    ],
)
def test_bad_wkt_is_explained(text, expected):
    problem = check_wkt(text)
    assert problem is not None and expected in problem


def test_a_bad_geom_raises_outside_a_collector():
    with pytest.raises(ValueError, match="not WKT"):
        columns_from_df(pl.DataFrame([{"col_id": "A", "geom": "0"}]), None)


def test_a_bad_geom_is_an_error_and_is_not_passed_on():
    """Dropped, so a dry run's write does not fail on it in PostGIS."""
    [col], collected = parse_columns(
        [{"col_id": "A", "lat": "53.2", "lng": "-119.1", "geom": "53.12, -119.15"}]
    )
    [notice] = collected.errors
    assert notice.code == "invalid-geometry"
    assert (notice.sheet, notice.row, notice.col_id, notice.column) == (
        "columns",
        2,
        "A",
        "geom",
    )
    assert col.geom is None and (col.lat, col.lng) == (53.2, -119.1)


def test_a_column_left_without_a_location_says_so():
    [col], collected = parse_columns(
        [{"col_id": "A", "geom": "37°19.162'N 118°10.707'W"}]
    )
    assert codes(collected) == ["invalid-geometry", "no-location"]


def test_a_bad_metadata_rgeom_is_reported_once_and_not_inherited():
    columns, collected = parse_columns(
        [
            {"col_id": "S1409", "lat": "53.19823", "lng": "-119.15147"},
            {"col_id": "S1412", "lat": "53.20036", "lng": "-119.4455"},
        ],
        meta={"project_name": "Mural", "rgeom": "0"},
    )
    [notice] = collected.errors
    assert (notice.code, notice.sheet, notice.column) == (
        "invalid-geometry",
        "metadata",
        "rgeom",
    )
    assert all(col.rgeom is None for col in columns)


def test_a_good_metadata_rgeom_is_inherited():
    square = "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
    [col], collected = parse_columns([{"col_id": "A"}], meta={"rgeom": square})
    assert col.rgeom == square
    assert not collected.has_errors


def test_a_column_with_no_location_at_all_is_an_error():
    """Caught here, where `column_utils.resolve_geometry` would raise on write."""
    _, collected = parse_columns([{"col_id": "road_river", "col_name": "Road River"}])
    [notice] = collected.errors
    assert (notice.code, notice.col_id) == ("no-location", "road_river")


# --- reference compilations -------------------------------------------------------


def refs_sheet(compilation) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ref_id": ["moghadam+_2025"],
            "authors": ["Moghadam"],
            "title": ["A title"],
            "date": ["2025"],
            "compilation": [compilation],
        }
    )


def test_an_unknown_compilation_is_warned_about_and_left_blank():
    with notices.collect_notices() as collected:
        [ref] = references_from_df(refs_sheet("225"), COMPILATION_CODES)

    assert ref.compilation_code == ""
    [notice] = collected.warnings
    assert (notice.code, notice.sheet, notice.row, notice.column) == (
        "unknown-compilation",
        "refs",
        2,
        "compilation",
    )
    assert "'225'" in notice.message and "`IODP`" in notice.message


@pytest.mark.parametrize(
    "given, stored", [("iodp", "IODP"), ("COSUNA II", "COSUNA II"), (None, "")]
)
def test_a_known_compilation_is_stored_as_the_enum_spells_it(given, stored):
    with notices.collect_notices() as collected:
        [ref] = references_from_df(refs_sheet(given), COMPILATION_CODES)
    assert ref.compilation_code == stored
    assert len(collected) == 0


# --- headers ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "header, field",
    [("b_pos*", "b_pos"), ("col_ id**", "col_id"), (" lithology ", "lithology")],
)
def test_headers_lose_stars_and_stray_spaces(header, field):
    assert clean_header(header) == field


def test_cleaning_headers_keeps_the_plain_field_when_both_are_given():
    df = pl.DataFrame({"b_pos*": [1.0], "b_pos": [2.0], "unit_name*": ["A"]})
    with notices.collect_notices() as collected:
        cleaned = clean_headers(df, "units")

    assert cleaned.columns == ["b_pos*", "b_pos", "unit_name"]
    assert cleaned["b_pos"].to_list() == [2.0]
    [notice] = collected.warnings
    assert (notice.code, notice.column) == ("ambiguous-columns", "b_pos*")


def test_starred_metadata_keys_are_read():
    from macrostrat.column_ingestion.metadata import metadata_from_df

    df = pl.DataFrame(
        {"key": ["project_name*", "col_type *"], "value": ["X", "measured"]}
    )
    meta = metadata_from_df(df)
    assert meta.project.name == "X" and meta.col_type == "section"
