"""
Write a Macrostrat database to a GeoPackage file using the GeoPandas library.

Currently, this represents the Macrostrat internal PostGIS schema more or less unmodified.
As a next step, we will rework it to fit the CriticalMAAS TA1 output schema.
https://github.com/DARPA-CRITICALMAAS/schemas/tree/main/ta1
"""

from macrostrat.database import Database
from geopandas import GeoDataFrame
from pathlib import Path
from rich import print


def write_map_geopackage(
    db: Database, identifier: str | int, filename: str = None, overwrite: bool = False
):
    """Write a Macrostrat map dataset (stored in PostGIS) to a GeoPackage file using GeoPandas and SQLAlchemy."""

    try:
        map_id = int(identifier)
        map_slug = get_scalar(
            db,
            "SELECT slug FROM maps.sources WHERE source_id = %(source_id)s",
            dict(source_id=map_id),
        )
    except ValueError:
        map_slug = identifier
        map_id = get_scalar(
            db,
            "SELECT source_id FROM maps.sources WHERE slug = %(slug)s",
            params=dict(slug=map_slug),
        )

    if filename is None:
        filename = f"{map_slug}.gpkg"

    print(f"Map [bold cyan]{map_slug}[/] (#{map_id}) -> {filename}")

    fn = Path(filename)
    file_exists = fn.exists()
    if file_exists and not overwrite:
        raise FileExistsError(f"File {filename} already exists")

    if file_exists and overwrite:
        fn.unlink()

    params = {"source_id": map_id}

    sources_query = """
    SELECT
    source_id,
    slug,
    name,
    url,
    ref_title,
    authors,
    ref_year,
    ref_source,
    isbn_doi,
    scale,
    licence, 
    rgeom bounds
    FROM maps.sources
    WHERE source_id = %(source_id)s
    """

    # Copy metadata
    df = GeoDataFrame.from_postgis(
        sources_query, db.engine, geom_col="bounds", params=params
    )
    df.to_file(filename, layer="map_meta", driver="GPKG")

    # Write map layers to GeoPackage
    for layer in ["points", "lines", "polygons"]:
        df = GeoDataFrame.from_postgis(
            f"SELECT * FROM maps.{layer} WHERE source_id = %(source_id)s",
            db.engine,
            geom_col="geom",
            params=params,
        )
        print(f"{len(df)} {layer}")
        df.to_file(filename, layer=layer, driver="GPKG")


def get_scalar(db: Database, query: str, params: dict = None):
    """Return a scalar value from a SQL query."""
    return list(db.run_sql(query, params=params))[0].scalar()
