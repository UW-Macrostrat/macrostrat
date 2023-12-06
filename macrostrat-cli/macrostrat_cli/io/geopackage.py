"""
Write a Macrostrat database to a GeoPackage file using the GeoPandas library.
"""

from macrostrat.database import Database
from geopandas import GeoDataFrame
from pandas import read_sql
from sqlalchemy import create_engine
from pathlib import Path
from rich import print


def write_map_geopackage(
    db: Database, identifier: str | int, filename: str = None, overwrite: bool = False
):
    """Write a map dataset to a GeoPackage file."""

    try:
        map_id = int(identifier)
        map_slug = db.run_sql(
            "SELECT slug FROM maps.sources WHERE source_id = %s", params=[map_id]
        ).scalar()
    except ValueError:
        map_slug = identifier
        map_id = list(
            db.run_sql(
                "SELECT source_id FROM maps.sources WHERE slug = :slug",
                params=dict(slug=map_slug),
            )
        )[0].scalar()

    if filename is None:
        filename = f"{map_slug}.gpkg"

    print(f"Map [bold cyan]{map_slug}[/] (#{map_id}) -> {filename}")

    fn = Path(filename)
    file_exists = fn.exists()
    if file_exists and not overwrite:
        raise FileExistsError(f"File {filename} already exists")

    if file_exists and overwrite:
        fn.unlink()

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

    # Create SQLite database
    sqlite_engine = create_engine(f"sqlite:///{filename}")

    # Copy metadata
    df = GeoDataFrame.from_postgis(
        sources_query, db.engine, geom_col="bounds", params={"source_id": map_id}
    )
    df.to_file(filename, layer="map_meta", driver="GPKG")

    # Write map layers to GeoPackage
    for layer in ["points", "lines", "polygons"]:
        df = GeoDataFrame.from_postgis(
            f"SELECT * FROM maps.{layer} WHERE source_id = %s",
            db.engine,
            geom_col="geom",
            params=(map_id,),
        )
        print(f"{len(df)} {layer}")
        df.to_file(filename, layer=layer, driver="GPKG")
