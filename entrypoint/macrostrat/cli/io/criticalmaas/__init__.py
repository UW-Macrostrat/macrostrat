"""
Write a Macrostrat map to the CriticalMAAS TA1 Geopackage format

- https://github.com/DARPA-CRITICALMAAS/ta1-geopackage
- https://github.com/DARPA-CRITICALMAAS/schemas/tree/main/ta1
"""

from macrostrat.database import Database
from pathlib import Path
from rich import print
from criticalmaas.ta1_geopackage import GeopackageDatabase

from .helpers import get_map_identifier, _unlink_if_exists
from .steps import (
    _build_map_metadata,
    _build_line_types,
    _build_line_features,
    _build_point_types,
    _build_point_features,
    _build_polygon_types,
    _build_polygon_features,
)


def write_map_geopackage(
    db: Database, identifier: str | int, filename: str = None, overwrite: bool = False
):
    """Write a Macrostrat map dataset (stored in PostGIS) to a GeoPackage file using GeoPandas and SQLAlchemy."""

    _map = get_map_identifier(db, identifier)

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
