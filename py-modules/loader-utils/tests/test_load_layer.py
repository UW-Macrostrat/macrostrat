import geopandas as gpd
import pandas as pd
import pyogrio
from pytest import fixture, mark, raises
from shapely.geometry import LineString, Polygon

from macrostrat.loader_utils import LoadError, load_layer

SCHEMA = "loader_test"


@fixture(scope="module")
def gpkg(tmp_path_factory):
    """Mirrors a provincial map export: OBJECTID as the feature ID, a nullable integer."""
    path = tmp_path_factory.mktemp("layers") / "map.gpkg"
    polygons = gpd.GeoDataFrame(
        {
            "MapNumber": ["13A", None],
            "LEXICON_ID": pd.array([12, None], dtype="Int16"),
        },
        geometry=[
            Polygon([(0, 0), (1000, 0), (1000, 1000)]),
            Polygon([(0, 0), (0, 1000), (1000, 1000)]),
        ],
        crs="EPSG:26919",
    )
    pyogrio.write_dataframe(
        polygons, path, layer="polygons", layer_options={"FID": "OBJECTID"}
    )
    lines = gpd.GeoDataFrame(
        {"kind": ["fault"]}, geometry=[LineString([(0, 0), (5, 5)])], crs="EPSG:26919"
    )
    pyogrio.write_dataframe(lines, path, layer="lines")
    pyogrio.write_dataframe(
        pd.DataFrame({"code": ["A", "B"]}), path, layer="units", append=True
    )
    return path


def _types(result):
    return dict(zip(result.columns, result.types))


def test_dry_run_structure(gpkg):
    result = load_layer(
        None,
        gpkg,
        "polygons",
        fid_column="objectid",
        promote_to_multi=True,
        dry_run=True,
    )
    assert _types(result) == {
        "objectid": "bigint",
        "map_number": "text",
        # Nulls widen the integer to float in pandas; the declared type wins.
        "lexicon_id": "smallint",
        "geom": "geometry(MultiPolygon, 4326)",
    }
    assert result.features == 2
    assert result.copied is None


def test_attribute_only_layer(gpkg):
    result = load_layer(None, gpkg, "units", dry_run=True)
    assert result.columns == ["code"]
    assert result.geometry_type is None


def test_replace_and_append_conflict(gpkg):
    with raises(LoadError):
        load_layer(None, gpkg, "lines", replace=True, append=True)


@fixture(scope="module")
def scratch(empty_db):
    empty_db.run_sql("CREATE EXTENSION IF NOT EXISTS postgis", raise_errors=True)
    empty_db.run_sql(f"CREATE SCHEMA {SCHEMA}", raise_errors=True)
    try:
        yield empty_db
    finally:
        empty_db.run_sql(f"DROP SCHEMA {SCHEMA} CASCADE", raise_errors=True)


@mark.docker
def test_load_layers(scratch, gpkg):
    engine = scratch.engine
    kw = dict(schema=SCHEMA, promote_to_multi=True)
    polygons = load_layer(
        engine, gpkg, "polygons", table="polygons", fid_column="objectid", **kw
    )
    units = load_layer(engine, gpkg, "units", table="units", **kw)
    assert (polygons.copied, units.copied) == (2, 2)

    rows = scratch.run_query(
        f"SELECT objectid, map_number, lexicon_id, ST_SRID(geom) srid, "
        f"GeometryType(geom) type FROM {SCHEMA}.polygons ORDER BY objectid"
    ).all()
    assert [tuple(r) for r in rows] == [
        (1, "13A", 12, 4326, "MULTIPOLYGON"),
        (2, None, None, 4326, "MULTIPOLYGON"),
    ]
    codes = scratch.run_query(
        f"SELECT code FROM {SCHEMA}.units ORDER BY code"
    ).scalars()
    assert list(codes) == ["A", "B"]
    # Release the session's locks; load_layer replaces on its own connection.
    scratch.session.commit()

    with raises(LoadError):
        load_layer(engine, gpkg, "units", table="units", **kw)
    again = load_layer(engine, gpkg, "units", table="units", replace=True, **kw)
    assert again.copied == 2
