from pathlib import Path


def ingest_gdb_domain_fields(gdb: Path, layer: str):
    """Ingest fields from a GDB domain."""
    from osgeo import ogr, gdal

    ds = ogr.Open(str(gdb))
    if ds is None:
        raise ValueError(f"Could not open GDB: {gdb}")

    return gdal.VectorInfo(ds, format="json")
