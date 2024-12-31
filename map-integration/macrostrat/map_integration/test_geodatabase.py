# M173_Temuco-NuevaImperial.gdb.tar.gz

from pathlib import Path

from osgeo import gdal, ogr
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
            assert domain_name == "LV_ATT_EPOCA"
            domain = domains[domain_name]
            assert domain["type"] == "coded"
            assert domain["codedValues"] is not None


def get_domains_for_field(gdb, layer):

    ds = ogr.Open(str(gdb))
    res = gdal.VectorInfo(ds, format="json")

    df = create_dataframe_for_layer(gdb, layer)

    assert df is not None
    assert len(df) > 150
    assert "geometry" in df.columns

    assert "domains" in res

    domains = res["domains"]

    lyr = None
    for l in res["layers"]:
        if l["name"] == layer:
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
            assert domain_name == "LV_ATT_EPOCA"
            domain = domains[domain_name]
            assert domain["type"] == "coded"
            assert domain["codedValues"] is not None

    return df


def get_layer_info(gdb, layer):
    ds = ogr.Open(str(gdb))
    res = gdal.VectorInfo(ds, format="json")

    lyr = None
    for l in res["layers"]:
        if l["name"] == layer:
            lyr = l
            break

    assert lyr is not None

    for field in lyr["fields"]:
        domains = res["domains"]

        if domain_name := field.get("domainName", None):
            domain = domains[domain_name]
            if domain["type"] == "coded":
                field["codedValues"] = domain["codedValues"]

    # Recast fields as a dictionary
    lyr["fields"] = {f["name"]: f for f in lyr["fields"]}

    return lyr


def test_apply_domains(gdb_fn):
    layer = "GB_UNIDAD_GEO_P"
    df = create_dataframe_for_layer(gdb_fn, layer)
    info = get_layer_info(gdb_fn, layer)

    field = info["fields"]["EPOCA_ESTRAT_MAX"]
    assert field["domainName"] == "LV_ATT_EPOCA"
    assert len(field["codedValues"]) > 0

    for col in df.columns:
        if col in info["fields"]:
            field = info["fields"][col]
            if "codedValues" in field:
                df[col] = df[col].apply(lambda x: field["codedValues"].get(x, x))
            if "alias" in field:
                df = df.rename(columns={col: field["alias"]})

    assert "Epoca (maxima)" in df.columns
    assert "Epoca (minima)" in df.columns
    assert "Tipo de Unidad" in df.columns

    assert "Eoceno" in df["Epoca (maxima)"].unique()
