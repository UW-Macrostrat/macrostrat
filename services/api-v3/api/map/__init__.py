from pathlib import Path
from typing import Annotated

import morecantile
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Path as PathParam
from morecantile import Tile
from shapely import GEOSException
from shapely.geometry import Point, Polygon
from shapely.wkb import loads as load_wkb
from shapely.wkt import loads as load_wkt
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from api.database import DatabaseDep

from .models import MapUnit

router = APIRouter(tags=["map"])

tms = morecantile.tms.get("WebMercatorQuad")

_queries = Path(__file__).parent / "queries"


def _query(name: str):
    return text((_queries / f"{name}.sql").read_text())


# Templated before it becomes a statement: `::owners` is filled per request.
_LEGEND_SQL = (_queries / "legend.sql").read_text()


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


#: Most legend entries to return. `carto`'s whole legend at a zoom is tens of
#: thousands; the cap keeps an `all` request a response rather than a dump.
DEFAULT_LEGEND_LIMIT = 5_000
MAX_LEGEND_LIMIT = 50_000

#: `legend.sql`'s owners in view: each map with a face there, with the part of
#: the view it owns; or, without faces, the answering source over the whole view.
# The layer and the view are scalar subqueries, not joins, so the planner
# reads them as constants and reaches `map_face`'s layer and spatial indexes.
_OWNERS_VISIBLE = """
  SELECT
    mf.map_id,
    ST_UnaryUnion(ST_Collect(ST_ClipByBox2D(mf.geometry, (SELECT g FROM view))))
      AS geometry
  FROM map_bounds_topology.map_face mf
  WHERE mf.map_layer = (SELECT layer_id FROM target)
    AND ST_Intersects(mf.geometry, (SELECT g FROM view))
    AND map_bounds.has_content(mf.map_id)
  GROUP BY mf.map_id
  UNION ALL
  SELECT t.source_id, (SELECT g FROM view)
  FROM target t
  WHERE t.layer_id IS NULL
"""

#: Every owner, and no geometry: the whole legend of each.
_OWNERS_ALL = """
  SELECT DISTINCT mf.map_id, NULL::geometry AS geometry
  FROM map_bounds_topology.map_face mf
  WHERE mf.map_layer = (SELECT layer_id FROM target)
    AND map_bounds.has_content(mf.map_id)
  UNION ALL
  SELECT t.source_id, NULL::geometry
  FROM target t
  WHERE t.layer_id IS NULL
"""

_LEGACY_LEGEND = text(
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
"""
)


@router.get(
    "/{ident}/legend",
    summary="The legend of a map or compilation",
)
async def get_map_legend(
    ident: Annotated[
        str,
        PathParam(
            description=(
                "A map or compilation slug, or an integer source id. "
                "`sys:carto-legacy` reads the materialized carto build."
            )
        ),
    ],
    database: DatabaseDep,
    bounds: Annotated[
        str | None,
        Query(description="Only the entries drawn within this area (WKT or bbox)"),
    ] = None,
    zoom: Annotated[
        int | None,
        Query(description="The zoom whose drawing is described; picks `carto`'s layer"),
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=MAX_LEGEND_LIMIT, description="Most entries to return")
    ] = DEFAULT_LEGEND_LIMIT,
):
    """The legend entries a source draws at a zoom, youngest first.

    With `bounds`, only the entries drawn within it (`visible`); without, every
    entry of every map the source draws at that zoom (`all`). Resolved the way
    the tiles are, so the legend matches the map: `carto` answers from its
    member at the zoom's scale, a compilation through its faces, a map from its
    own polygons. `zoom` defaults to the most detailed.
    """
    geometry = None
    if bounds is not None:
        geometry = parse_bounds(bounds)
    if zoom is None:
        zoom = 23

    async with database.async_connection() as conn:
        await conn.execute(
            text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
        )

        if ident == LEGACY_CARTO:
            if geometry is None:
                raise HTTPException(400, "The legacy build's legend needs `bounds`.")
            res = await conn.execute(
                _LEGACY_LEGEND,
                {"bounds": geometry.wkt, "scale": scale_for_zoom(zoom)},
            )
            return res.mappings().all()

        known = await conn.execute(
            text("SELECT map_bounds.resolve_source(CAST(:ident AS text))"),
            {"ident": ident},
        )
        if known.scalar() is None:
            raise HTTPException(404, f"No map or compilation matching '{ident}'")

        owners = _OWNERS_ALL
        params = {"ident": ident, "zoom": zoom, "limit": limit}
        if geometry is not None:
            owners = _OWNERS_VISIBLE
            params["bounds"] = geometry.wkt
        sql = text(_LEGEND_SQL.replace("::owners", owners))
        try:
            res = await conn.execute(sql, params)
        except DBAPIError as err:
            if not _is_timeout(err):
                raise
            raise HTTPException(
                504, "The legend query timed out; ask for a smaller area."
            ) from err
        return res.mappings().all()


# --- Units at a location ---

#: The materialized `carto.*` build, addressed like a compilation. Answered by
#: `map_bounds.units_at` itself; never a `maps.sources` row, so the existence
#: check below skips it. It exists to measure the compilation system against the
#: legacy build on the same route, and goes with Stage D.
LEGACY_CARTO = "sys:carto-legacy"

# How long the database is allowed to spend on one units request.
#
# The route is a point lookup and answers in tens of milliseconds; what can run
# away is `bounds`, which a caller may set to a continent and which is asked of
# every layer of a stack at once. Without this, such a request pins a backend
# for as long as it takes -- and killing the client does not stop it, because
# the query keeps running until the server notices the socket is gone. A
# timeout is what makes "this cannot block forever" true rather than hoped for.
STATEMENT_TIMEOUT_MS = 10_000

#: Widest `bounds` this route will answer, as a span in degrees.
#
# Not a cost model — degrees are not equal-area — but a sanity guard, and one
# whose answer a caller can predict. Measured against the local database, a 1°
# box answers in ~110 ms and a 4° box in ~1.5 s; 10° exceeds the timeout above.
# Past a few degrees the question has stopped being "what is mapped here",
# which is what this route is for; `bounds` is meant for a click tolerance or a
# small viewport.
MAX_BOUNDS_SPAN = 5.0

#: Most units to return. Caps the response rather than the work -- the timeout
#: above is what bounds the work -- so a huge area fails loudly instead of
#: serializing a million rows.
DEFAULT_LIMIT = 500
MAX_LIMIT = 5_000


class MapLocation:
    """Where to ask, and at what zoom.

    `lng`/`lat` is taken as a **point**, not as the tile containing it. This
    route asks what is mapped at a place, and the tile a location falls in is a
    quarter of a hemisphere at low zoom -- sizing the query from it turns a
    point question into an area scan of millions of polygons. `zoom` therefore
    only chooses which layer of a stack is the current one.

    `bounds` is an explicit area and is used as given, the same as
    `/{compilation}/legend`.
    """

    def __init__(self, geometry, zoom: int):
        self.geometry = geometry
        self.zoom = zoom


def map_location_params(
    bounds: str = None, lng: float = None, lat: float = None, zoom: int = None
) -> MapLocation:
    """`bounds`, or `lng`/`lat` with an optional `zoom`, read for a point query."""
    if bounds is not None:
        geometry = parse_bounds(bounds)
        check_bounds_span(geometry)
        if zoom is None:
            zoom = min_bounding_tile(geometry).z + 1
        return MapLocation(geometry, zoom)

    if lat is None or lng is None:
        raise HTTPException(400, "Either bounds, or lng and lat, must be provided.")

    # No zoom means "the most detailed answer is the current one".
    if zoom is None:
        zoom = 23
    return MapLocation(Point(lng, lat), zoom)


def check_bounds_span(geometry) -> None:
    """Refuse an area too large to be a location.

    Up front, before any spatial work: the statement timeout below would stop a
    continent-sized request eventually, but spending ten seconds to say no is
    worse than saying it immediately, and a caller learns nothing from a
    timeout.
    """
    minx, miny, maxx, maxy = geometry.bounds
    span = max(maxx - minx, maxy - miny)
    if span <= MAX_BOUNDS_SPAN:
        return
    raise HTTPException(
        400,
        f"`bounds` spans {span:.1f}°, over the {MAX_BOUNDS_SPAN}° this route "
        "answers for. It reports what is mapped at a location; use the tiles "
        "for an area.",
    )


@router.get(
    "/{compilation}/units",
    summary="Map units at a location",
)
async def get_map_units(
    compilation: Annotated[
        str,
        PathParam(
            description=(
                "A map or compilation slug, or an integer source id. `carto` is "
                "the served map; `sys:carto-legacy` is the materialized build it "
                "replaces."
            )
        ),
    ],
    location: Annotated[MapLocation, Depends(map_location_params)],
    database: DatabaseDep,
    limit: Annotated[
        int, Query(ge=1, le=MAX_LIMIT, description="Most units to return")
    ] = DEFAULT_LIMIT,
) -> list[MapUnit]:
    """Every mapped polygon covering a location, with where each came from.

    Polygon granularity, where `/{compilation}/legend` is legend granularity:
    the question here is "what is mapped at this point, and by which map", which
    is the one the compilation system answers differently from the materialized
    carto tables -- a polygon arrives with the map that owns it, the face it
    sits in, and the member of the compilation it is presented as.

    Resolution is `map_bounds.units_at`, the same entry point the tiles and the
    v2 point lookup read through, so the answer is what the tiles draw rather
    than a second opinion assembled another way. A multiscale compilation
    (`carto`) answers from the member whose scale band contains `zoom`; any
    other compilation or map answers for itself at every zoom.

    Takes `bounds`, or `lng`/`lat` with an optional `zoom` -- the same location
    parameters as `/{compilation}/legend`, but `lng`/`lat` means the point
    rather than the tile around it. With `bounds` this is an area query and
    returns everything intersecting the box.
    """
    async with database.async_connection() as conn:
        # Bounded before anything spatial runs, and `LOCAL` so it lapses with
        # this transaction rather than following the connection back to the pool.
        await conn.execute(
            text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
        )

        if compilation != LEGACY_CARTO:
            known = await conn.execute(
                text("SELECT map_bounds.resolve_source(CAST(:ident AS text))"),
                {"ident": compilation},
            )
            if known.scalar() is None:
                raise HTTPException(
                    404, f"No map or compilation matching '{compilation}'"
                )

        params = {
            "ident": compilation,
            "bounds": location.geometry.wkt,
            "zoom": location.zoom,
            "limit": limit,
        }
        try:
            res = await conn.execute(_query("units"), params)
        except DBAPIError as err:
            if not _is_timeout(err):
                raise
            raise HTTPException(
                504,
                "The units query timed out. This route is a point lookup; a "
                "`bounds` covering more than a small area is too much to ask "
                "of it.",
            ) from err

        return [MapUnit(**row) for row in res.mappings()]


def _is_timeout(err: DBAPIError) -> bool:
    """Whether a driver error is the statement timeout firing.

    By SQLSTATE off the wrapped driver exception, since both psycopg and
    asyncpg reach here and spell the exception class differently.
    """
    sqlstate = getattr(err.orig, "sqlstate", None) or getattr(err.orig, "pgcode", None)
    return sqlstate == "57014"
