from pathlib import Path
from typing import Annotated

import morecantile
from fastapi import APIRouter, HTTPException, Query
from fastapi import Path as PathParam
from morecantile import Tile
from shapely import GEOSException
from shapely.geometry import Polygon
from shapely.wkb import loads as load_wkb
from shapely.wkt import loads as load_wkt
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from api.database import DatabaseDep

router = APIRouter(tags=["map"])

tms = morecantile.tms.get("WebMercatorQuad")

_queries = Path(__file__).parent / "queries"


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


#: The materialized `carto.*` build, addressed like a compilation. Never a
#: `maps.sources` row, so the existence check below skips it. It exists to
#: measure the compilation system against the legacy build on the same route,
#: and goes with Stage D.
LEGACY_CARTO = "sys:carto-legacy"

# How long the database is allowed to spend on one legend request.
#
# Without this, a large `bounds` pins a backend for as long as it takes -- and
# killing the client does not stop it, because the query keeps running until the
# server notices the socket is gone. A timeout is what makes "this cannot block
# forever" true rather than hoped for.
STATEMENT_TIMEOUT_MS = 10_000

#: Widest `bounds` this route will answer, in tiles at the request's zoom.
#
# Not a cost model — degrees are not equal-area — but a sanity guard, and one
# whose answer a caller can predict. An area is answered at the detail of its
# zoom, so what is reasonable scales with it: a continent at zoom 11 is not a
# view. Eight tiles of 512 px is a 4K viewport at a whole zoom.
MAX_BOUNDS_TILES = 8


def max_bounds_span(zoom: int) -> float:
    """The widest `bounds` answered at `zoom`, as a span in degrees."""
    return MAX_BOUNDS_TILES * 360 / 2**zoom


def check_bounds_span(geometry, zoom: int) -> None:
    """Refuse an area too large to be a view at `zoom`.

    Up front, before any spatial work: the statement timeout would stop a
    continent-sized request eventually, but spending ten seconds to say no is
    worse than saying it immediately, and a caller learns nothing from a
    timeout.
    """
    minx, miny, maxx, maxy = geometry.bounds
    span = max(maxx - minx, maxy - miny)
    limit = max_bounds_span(zoom)
    if span <= limit:
        return
    raise HTTPException(
        400,
        f"`bounds` spans {span:.3g}°, over the {limit:.3g}° this route answers "
        f"for at zoom {zoom}.",
    )


def check_served_zoom(ident: str, zoom: int, min_zoom: int | None) -> None:
    """Refuse a zoom below the ones the source is drawn at.

    Its tiles hold nothing there (`map_bounds.zoom_range`), so neither does
    its legend. Above the range a client overzooms the last tiles, and the
    answer is theirs.
    """
    if min_zoom is None or zoom >= min_zoom:
        return
    raise HTTPException(
        400,
        f"'{ident}' is drawn from zoom {min_zoom}; zoom {zoom} is below it.",
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
    own polygons. `zoom` defaults to the one `bounds` fills, or without it to the
    most detailed. A zoom below the ones the source is drawn at is refused, as is
    a `bounds` more than eight tiles across at the zoom.
    """
    geometry = None
    if bounds is not None:
        geometry = parse_bounds(bounds)
        if zoom is None:
            zoom = min_bounding_tile(geometry).z + 1
        check_bounds_span(geometry, zoom)
    if zoom is None:
        zoom = 23

    async with database.async_connection() as conn:
        # Bounded before anything spatial runs, and `LOCAL` so it lapses with
        # this transaction rather than following the connection back to the pool.
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

        source = (
            await conn.execute(
                text(
                    """
                    SELECT s.id, zr.min_zoom
                    FROM (
                      SELECT map_bounds.resolve_source(CAST(:ident AS text)) AS id
                    ) s
                    LEFT JOIN LATERAL map_bounds.zoom_range(s.id) zr ON true
                    """
                ),
                {"ident": ident},
            )
        ).one()
        if source.id is None:
            raise HTTPException(404, f"No map or compilation matching '{ident}'")
        check_served_zoom(ident, zoom, source.min_zoom)

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


def _is_timeout(err: DBAPIError) -> bool:
    """Whether a driver error is the statement timeout firing.

    By SQLSTATE off the wrapped driver exception, since both psycopg and
    asyncpg reach here and spell the exception class differently.
    """
    sqlstate = getattr(err.orig, "sqlstate", None) or getattr(err.orig, "pgcode", None)
    return sqlstate == "57014"
