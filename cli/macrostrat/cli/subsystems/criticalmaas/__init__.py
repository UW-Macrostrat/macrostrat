"""
Write a Macrostrat map to the CriticalMAAS TA1 Geopackage format

- https://github.com/DARPA-CRITICALMAAS/ta1-geopackage
- https://github.com/DARPA-CRITICALMAAS/schemas/tree/main/ta1
"""

from asyncio import run
from pathlib import Path

from criticalmaas.ta1_geopackage import GeopackageDatabase
from rich import print
from typer import Argument, Typer

from macrostrat.cli.database import get_db
from macrostrat.database import Database

from .helpers import _unlink_if_exists
from .importer import import_criticalmaas
from .steps import (
    _build_line_features,
    _build_line_types,
    _build_map_metadata,
    _build_point_features,
    _build_point_types,
    _build_polygon_features,
    _build_polygon_types,
)


def read_map_geopackage(filename: str):
    """Read a Macrostrat map dataset from a GeoPackage file using GeoPandas and SQLAlchemy."""

    gpd = GeopackageDatabase(filename)

    # Get models automapped from the Geopackage schema
    Map = gpd.model.map
    MapMetadata = gpd.model.map_metadata
    LineType = gpd.model.line_type
    PolygonType = gpd.model.polygon_type
    GeologicUnit = gpd.model.geologic_unit
    PointType = gpd.model.point_type

    # Read the map metadata
    map_metadata = gpd.read_models(MapMetadata)

    # Read the line features
    line_features = gpd.read_features("line_feature")

    # Read the point features
    point_features = gpd.read_features("point_feature")

    # Read the polygon features
    polygon_features = gpd.read_features("polygon_feature")

    return {
        "map": gpd.read_models(Map),
        "map_metadata": map_metadata,
        "line_types": gpd.read_models(LineType),
        "line_features": line_features,
        "point_types": gpd.read_models(PointType),
        "point_features": point_features,
        "polygon_types": gpd.read_models(PolygonType),
        "geologic_units": gpd.read_models(GeologicUnit),
        "polygon_features": polygon_features,
    }


def write_map_geopackage(
    db: Database, identifier: str | int, filename: str = None, overwrite: bool = False
):
    """Write a Macrostrat map dataset (stored in PostGIS) to a GeoPackage file using GeoPandas and SQLAlchemy."""

    _map = None

    if filename is None:
        filename = Path(f"{_map.slug}.gpkg")
    _unlink_if_exists(filename, overwrite=overwrite)

    print(f"Map [bold cyan]{_map.slug}[/] (#{_map.id}) -> {filename}")

    # Create the GeoPackage
    gpd = GeopackageDatabase(filename)

    # Get models automapped from the Geopackage schema
    Map = gpd.model.map
    MapMetadata = gpd.model.map_metadata
    LineType = gpd.model.line_type
    PolygonType = gpd.model.polygon_type
    GeologicUnit = gpd.model.geologic_unit
    PointType = gpd.model.point_type

    ### MAP metadata ###

    gpd.write_models(_build_map_metadata(db, _map, Map, MapMetadata))

    ### LINE FEATURES ###

    # Insert the line types
    valid_types = gpd.enum_values("line_type")
    gpd.write_models(_build_line_types(db, _map, LineType, valid_types))
    gpd.write_features("line_feature", _build_line_features(db, _map))

    ### POINT FEATURES ###
    valid_types = gpd.enum_values("point_type")
    gpd.write_models(_build_point_types(db, _map, PointType, valid_types))
    gpd.write_features("point_feature", _build_point_features(db, _map))

    ### POLYGON FEATURES ###

    gpd.write_models(_build_polygon_types(db, _map, PolygonType, GeologicUnit))
    gpd.write_features("polygon_feature", _build_polygon_features(db, _map))


app = Typer(no_args_is_help=True)


@app.command(name="import")
def _import_criticalmaas(file: Path):
    """Import a CriticalMAAS TA1 Geopackage into Macrostrat"""
    run(import_criticalmaas(file))


@app.command(name="export")
def write_map_geopackage(
    map: str = Argument(...), filename: Path = None, overwrite: bool = False
):
    """Write a CriticalMAAS geopackage from a map"""
    db = get_db()
    write_map_geopackage(db, map, filename, overwrite=overwrite)
