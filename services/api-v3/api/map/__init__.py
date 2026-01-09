from typing import Annotated

import morecantile
from fastapi import APIRouter, HTTPException
from fastapi import Depends
from morecantile import Tile
from shapely import GEOSException
from shapely.geometry import Polygon
from shapely.wkb import loads as load_wkb
from shapely.wkt import loads as load_wkt

from api.database import get_sync_database

router = APIRouter(tags=["map"])

tms = morecantile.tms.get("WebMercatorQuad")


class MapAreaInfo:
    def __init__(self, bounds: Polygon, zoom: int):
        self.bounds = bounds
        self.zoom = zoom


def map_area_params(
    bounds: str = None, lat: float = None, lng: float = None, zoom: int = None
) -> MapAreaInfo:
    """Dependency to get map area information."""

    if bounds is not None:
        _bounds = parse_bounds(bounds)
        zoom = min_bounding_tile(_bounds).z + 1
        return MapAreaInfo(bounds=_bounds, zoom=zoom)

    if lat is None or lng is None:
        raise HTTPException(400, "Either bounds or and lat,lng,zoom must be provided.")
    if zoom is None:
        zoom = 23
    tile = tms.tile(lng=lng, lat=lat, zoom=zoom)
    _bounds = tile_polygon(tile)
    return MapAreaInfo(bounds=_bounds, zoom=zoom)

    # Calculate bounds from lat, lng, zoom


def tile_polygon(tile: Tile) -> Polygon:
    """Get the polygon for a given tile."""
    bbox = tms.bounds(tile)
    return Polygon.from_bounds(bbox.left, bbox.bottom, bbox.right, bbox.top)


def min_bounding_tile(geometry: Polygon) -> Tile:
    """Get the bounding tile for a given geometry."""
    minx, miny, maxx, maxy = geometry.bounds
    z = 0
    for z in range(0, 23):
        ul_tile = tms.tile(lng=minx, lat=maxy, zoom=z)
        lr_tile = tms.tile(lng=maxx, lat=miny, zoom=z)
        if ul_tile != lr_tile:
            break
    return tms.tile(lng=minx, lat=maxy, zoom=z - 1)


def parse_bounds(bounds: str) -> Polygon:
    """Parse bounds string into a tuple of floats."""

    try:
        # Check if bounds is a WKB hex string
        return load_wkb(bounds, hex=True)
    except GEOSException:
        pass

    try:
        # Check if bounds is a WKT POLYGON
        return load_wkt(bounds)
    except GEOSException:
        pass

    # Try to parse as comma-separated values
    try:
        west, south, east, north = map(float, bounds.split(","))
        return Polygon.from_bounds(west, south, east, north)
    except ValueError:
        raise HTTPException(
            400,
            "Invalid bounds format. Expected WKB hex, WKT POLYGON, or comma-separated values (west,south,east,north).",
        )


def scale_for_zoom(z: int, dz: int = 0):
    _z = z - dz
    if _z < 3:
        return "tiny"
    elif _z < 6:
        return "small"
    elif _z < 9:
        return "medium"
    else:
        return "large"


def get_compilation(compilation: str) -> str:
    """Dependency to validate compilation parameter."""
    valid_compilations = ["carto"]
    if compilation not in valid_compilations:
        raise ValueError(
            f"Invalid compilation '{compilation}'. Valid options are: {valid_compilations}"
        )
    return compilation


@router.get(
    "/{compilation}/legend",
    summary="Get map service status",
)
def get_map_legend(
    compilation: Annotated[str, Depends(get_compilation)],
    map_area: Annotated[MapAreaInfo, Depends(map_area_params)],
):
    """Get the legend for a given map compilation."""

    db = get_sync_database()

    scale = scale_for_zoom(map_area.zoom)

    if compilation != "carto":
        raise HTTPException(
            status_code=400,
            detail="Only 'carto' compilation is currently supported.",
        )

    res = db.run_query(
        """
        WITH polygons AS (
            SELECT legend_id, source_id, scale
            FROM carto.polygons p
            JOIN maps.map_legend ml
            USING (map_id)
            WHERE p.scale = :scale
              AND st_intersects(p.geom, ST_SetSRID(ST_GeomFromText(:bounds), 4326))
            GROUP BY legend_id, source_id, scale
        )
        SELECT legend_id,
               m.source_id,
               s.scale,
               REGEXP_REPLACE(m.name, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g')     AS map_unit_name,
               REGEXP_REPLACE(strat_name, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g') AS strat_name,
               age,
               REGEXP_REPLACE(lith, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g')       AS lith,
               REGEXP_REPLACE(descrip, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g')    AS descrip,
               REGEXP_REPLACE(comments, E'[\\n\\r\\f\\u000B\\u0085\\u2028\\u2029]+', ' ', 'g')   AS comments,
               best_age_top::float                                                                           t_age,
               best_age_bottom::float                                                                        b_age,
               m.b_interval,
               m.t_interval,
               strat_name_ids                                                                                strat_name_id,
               unit_ids                                                                                      unit_id,
               lith_classes,
               lith_types,
               lith_ids                                                                                      lith_id,
               color,
               m.area::float,
               tiny_area::float,
               small_area::float,
               medium_area::float,
               large_area::float
        FROM maps.legend m
        JOIN maps.sources s USING (source_id)
        JOIN polygons p USING (legend_id, source_id)
        """,
        params={"bounds": map_area.bounds.wkt, "scale": scale},
    ).mappings().all()

    return res
