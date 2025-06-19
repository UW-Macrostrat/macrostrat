from functools import lru_cache
from pathlib import Path


@lru_cache
def get_vector_info(dataset: Path):
    from osgeo import gdal, ogr

    """Get information on fields and layers (high-level function roughly equivalent to ogrinfo)"""
    ogr.UseExceptions()
    return gdal.VectorInfo(str(dataset), format="json")


def get_layer_names(ds: Path):
    info = get_vector_info(ds)
    return [lyr["name"] for lyr in info["layers"]]


def _get_basic_layer_info(info, layer):
    for lyr in info["layers"]:
        if lyr["name"] == layer:
            return lyr


def get_layer_info(ds: Path, layer: str):
    info = get_vector_info(ds)
    lyr = _get_basic_layer_info(info, layer)
    domains = info["domains"]

    for field in lyr["fields"]:
        if domain_name := field.get("domainName", None):
            domain = domains[domain_name]
            if domain["type"] == "coded":
                field["codedValues"] = domain["codedValues"]

    # Recast fields as a dictionary
    lyr["fields"] = {f["name"]: f for f in lyr["fields"]}

    return lyr


def apply_domains_to_fields(df, info):
    """Apply coded 'domain' values to fields in a dataframe.
    This improves handling of ESRI GeoDatabases, particularly, and might be
    applicable to other file types like GeoPackages.
    """

    for col in df.columns:
        if col in info["fields"]:
            field = info["fields"][col]
            if "codedValues" in field:
                df[col] = df[col].apply(lambda x: field["codedValues"].get(x, x))
            if "alias" in field:
                df = df.rename(columns={col: field["alias"]})

    return df
