# M173_Temuco-NuevaImperial.gdb.tar.gz

from pathlib import Path

from pytest import fixture

from map_integration.commands.ingest import create_dataframe_for_layer
from map_integration.pipeline import ingestion_context

fixtures_dir = Path(__file__).parent.parent.parent / "test-fixtures"


@fixture
def gdb_fn():
    fn = fixtures_dir / "M173_Temuco-NuevaImperial.gdb.tar.gz"
    with ingestion_context(fn) as tmp_dir:
        yield tmp_dir / "M173_Temuco-NuevaImperial.gdb"


def test_get_geodatabase_domains(gdb_fn):
    from osgeo import gdal, ogr

    ds = ogr.Open(str(gdb_fn))
    res = gdal.VectorInfo(ds, format="json")

    lyr_name = "GB_UNIDAD_GEO_P"

    df = create_dataframe_for_layer(gdb_fn, lyr_name)

    assert df is not None
    assert len(df) > 150
    assert "geometry" in df.columns
    assert "EPOCA_ESTRAT_MAX" in df.columns
    assert "EPOCA_ESTRAT_MIN" in df.columns

    assert "domains" in res

    domains = res["domains"]

    lyr = None
    for l in res["layers"]:
        if l["name"] == lyr_name:
            lyr = l
            break

    assert lyr is not None

    fields = lyr["fields"]

    for field in fields:
        assert field["name"] in df.columns

        if field["name"] == "EPOCA_ESTRAT_MAX":
            assert field["alias"] == "Epoca (maxima)"
            domain_name = field.get("domainName", None)
            assert domain_name is not None
            domain = domains[domain_name]
            assert domain["type"] == "coded"
            assert domain["codedValues"] is not None
