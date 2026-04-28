"""
Basic tests for the creation of Macrostrat columns.
"""

from io import StringIO

from polars import read_csv

from .units import get_units_from_df

# Wkt for a basic point-based stratigraphic column
basic_column_wkt = "POINT (0 0)"  # null island
# CSV with header for a stratigraphic column
basic_units_csv = """
col_id|pos|name|lith|b_int|b_prop
1|200|||Cambrian|0.2
1|100|Silex Formation|sandstone||
1|0|Brubaker Formation|shale|Cambrian|0.1
"""

basic_units_fobj = StringIO(basic_units_csv)


def test_ingest_units():
    """Ingest basic column into the Macrostrat database"""
    df = read_csv(basic_units_fobj, separator="|")
    assert df.shape == (3, 6)
    col_units = get_units_from_df(df)

    assert len(col_units) == 1
    assert "1" in col_units

    units = col_units["1"]

    assert len(units) == 2

    # Sort units by pos
    units = sorted(units, key=lambda u: u.b_pos)

    assert units[0].name == "Brubaker Formation"
    assert units[0].b_pos == 0
    assert units[0].t_pos == 100
    assert units[1].name == "Silex Formation"
    assert units[1].b_pos == 100
    assert units[1].t_pos == 200


def test_db_ingest_units(test_db):
    """Test ingesting units into the database"""
    df = test_db.run_query("SELECT 1").one_or_none()
    assert df is not None
    assert df[0] == 1
    # res = test_db.run_query("SELECT count(*) FROM macrostrat.cols").scalar()
    # assert res == 0
