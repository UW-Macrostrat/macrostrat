"""Tiles for any source, by slug: `/map/{slug}/{z}/{x}/{y}`.

One route for every kind of source, resolved by its facts rather than by which
module happens to serve it. The request names a slug (or an integer id) and a
zoom, and the database says what answers for it:

- `map_bounds.serving_source` applies the multiscale hop -- `carto` at zoom 5
  is `carto-small` -- and is the identity for everything else;
- a source with faces (a served compilation) is drawn through its `map_face`
  coverage, `queries/faces.sql`, which is what `/dev/carto` did with a zoom
  `CASE` of its own;
- anything else -- a map, a mosaic member, a materialized compilation -- is the
  `tile_layers.map` stored function that `/map/{z}/{x}/{y}?source_id=` has
  always used, so those two routes agree by construction.

Every branch emits the same `units` and `lines` layers with the same
properties, so one Mapbox style draws any slug.

A source is drawn only within its zoom range (`map_bounds.zoom_range`: its scale
band, two zooms deeper, and its members' for a source without a scale); outside
it the tile is empty. `/map/{slug}/tilejson.json` publishes that range with the
source's bounds, so a client neither asks for those tiles nor has to look the
extent up elsewhere.

`sys:carto-legacy` is a reserved name, never a `maps.sources` row: it is the
`carto-slim` stored function under this route's address, so the compilation
system can be measured against the materialized build with nothing but the
slug changing. It goes with Stage D.

Cache and access follow the slug. Only `carto` (and the legacy alias, which
shares `carto-slim`'s rows) participates in the database-side tile cache, as
`carto` and `carto-slim` do today; everything else is computed per request.
And only those two are public: any other slug requires a delegated token
carrying `tiles:map`, the mechanism the guarded raster layers use, so the
per-request cost of an arbitrary compilation is spent for known callers.
"""

from enum import Enum
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from buildpg import render
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from morecantile import Tile

from macrostrat.tileserver_utils import (
    CachedTileArgs,
    CacheMode,
    MimeTypes,
    TileParams,
    VectorTileResponse,
    handle_cached_tile_request,
)
from macrostrat.tileserver_utils.cache import get_layer_id
from macrostrat.utils import get_logger

from ..auth import bearer, require_scope
from ..utils import get_sql
from ..vector_tiles import TILE_RESPONSE_PARAMS

log = get_logger(__name__)

__here__ = Path(__file__).parent

router = APIRouter()
legacy_router = APIRouter()

#: The scope a delegated token must carry to request any slug but the public ones.
SCOPE = "tiles:map"

#: The materialized carto build, addressed like a compilation.
LEGACY_CARTO = "sys:carto-legacy"

#: Served without a token.
PUBLIC_SLUGS = frozenset({"carto", LEGACY_CARTO})

#: The tile-cache profile a slug's tiles are stored under; absent means no cache.
#: The legacy alias renders the `carto-slim` function with no parameters, which
#: is exactly a `/carto-slim/{z}/{x}/{y}` request, so it shares those rows.
CACHE_PROFILES = {"carto": "map-carto", LEGACY_CARTO: "carto-slim"}

_guard = require_scope(SCOPE)

# Which source answers, and how it is drawn. `resolve_source` takes a slug or an
# id as text. The source that answers at the zoom (`serving_source`, the
# multiscale hop) is drawn through its faces (`face_layer_for`), or without any,
# its polygons.
# Served-ness and the zoom range are the requested source's: `carto` is served
# though its tiers are not, and spans every zoom though each of them spans a few.
# A name that matches nothing comes back as a NULL `source_id`.
_RESOLVE = """
SELECT
  map_bounds.serving_source(r.source_id, :z) AS source_id,
  map_bounds.face_layer_for(r.source_id, :z) AS layer_id,
  map_bounds.is_served(r.source_id) AS is_served,
  zr.min_zoom,
  zr.max_zoom
FROM (SELECT map_bounds.resolve_source(:slug) AS source_id) r
CROSS JOIN LATERAL map_bounds.zoom_range(r.source_id) zr
"""

# What a TileJSON document says about a source: its extent and zoom range.
_DESCRIBE = """
SELECT
  s.slug,
  s.name,
  map_bounds.is_served(s.source_id) AS is_served,
  zr.min_zoom,
  zr.max_zoom,
  ST_XMin(ma.geometry) AS west,
  ST_YMin(ma.geometry) AS south,
  ST_XMax(ma.geometry) AS east,
  ST_YMax(ma.geometry) AS north,
  -- Inside the footprint, so a view opened there shows the map; the middle of
  -- the bounds may not (`ngs-surface`'s is in the Pacific).
  ST_X(ST_PointOnSurface(ma.geometry)) AS center_lng,
  ST_Y(ST_PointOnSurface(ma.geometry)) AS center_lat,
  -- Solved at some zoom: its faces can be drawn where its units are not.
  EXISTS (
    SELECT 1 FROM map_bounds.scale_band sb
    WHERE map_bounds.face_layer_for(s.source_id, sb.min_zoom) IS NOT NULL
  ) AS has_faces
FROM maps.sources s
CROSS JOIN LATERAL map_bounds.zoom_range(s.source_id) zr
LEFT JOIN map_bounds.map_area ma ON ma.source_id = s.source_id
WHERE s.source_id = map_bounds.resolve_source(:slug)
"""

#: A TileJSON document's zooms where the source sets none: every zoom.
DEFAULT_MINZOOM = 0
DEFAULT_MAXZOOM = 22

#: Tiles across a view, for judging whether bounds fit it at the minimum zoom:
#: two 512 px tiles, a laptop-width map.
VIEW_TILES = 2

_FACES_SQL = get_sql(__here__ / "queries" / "faces.sql")


class Detail(str, Enum):
    """How much of the legend a unit carries.

    `slim`, the default, is the `tile_layers.map_legend_info` columns that
    `/carto-slim` has always carried. `full` adds the legend's own text,
    interval names and reference that `/carto` carries, so the one can stand in
    for the other. Only a source drawn through faces has `full`; a map drawn by
    `tile_layers.map` carries `slim` whatever is asked.
    """

    slim = "slim"
    full = "full"


# Filled into `faces.sql`'s `::detail_columns` / `::detail_joins` slots for
# `detail=full`: `/carto`'s properties, from the legend row itself.
_FULL_COLUMNS = """,
    COALESCE(lg.name, '') AS name,
    COALESCE(lg.age, '') AS age,
    COALESCE(lg.lith, '') AS lith,
    COALESCE(lg.descrip, '') AS descrip,
    COALESCE(lg.comments, '') AS comments,
    lg.t_interval AS t_int_id,
    COALESCE(ta.interval_name, '') AS t_int,
    lg.b_interval AS b_int_id,
    tb.interval_name AS b_int,
    COALESCE(ls.url, '') AS ref_url,
    COALESCE(ls.name, '') AS ref_name,
    COALESCE(ls.ref_title, '') AS ref_title,
    COALESCE(ls.authors, '') AS ref_authors,
    COALESCE(ls.ref_source, '') AS ref_source,
    COALESCE(ls.ref_year, '') AS ref_year,
    COALESCE(ls.isbn_doi, '') AS ref_isbn"""
_FULL_JOINS = """
  JOIN maps.legend lg ON lg.legend_id = l.legend_id
  LEFT JOIN macrostrat.intervals ta ON ta.id = lg.t_interval
  LEFT JOIN macrostrat.intervals tb ON tb.id = lg.b_interval
  LEFT JOIN maps.sources ls ON ls.source_id = lg.source_id"""


def faces_sql(detail: Detail) -> str:
    columns = ""
    joins = ""
    if detail == Detail.full:
        columns = _FULL_COLUMNS
        joins = _FULL_JOINS
    return _FACES_SQL.replace("::detail_columns", columns).replace(
        "::detail_joins", joins
    )


def is_public(slug: str) -> bool:
    return slug in PUBLIC_SLUGS


def cache_profile(slug: str, detail: Detail = Detail.slim) -> Optional[str]:
    """The profile a slug's tiles are cached under; `full` ones apart, since
    the same tile carries different properties."""
    profile = CACHE_PROFILES.get(slug)
    if profile is not None and detail == Detail.full:
        profile += "-full"
    return profile


@router.get("/{slug}/{z:int}/{x:int}/{y:int}", **TILE_RESPONSE_PARAMS)
async def map_tile(
    request: Request,
    background_tasks: BackgroundTasks,
    slug: str,
    tile: Tile = Depends(TileParams),
    cache: CacheMode = CacheMode.prefer,
    detail: Detail = Detail.slim,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    """A tile of any source: a map, a compilation, or `carto` itself.

    `slug` is a source slug or an integer id. `carto` and `sys:carto-legacy`
    are public; every other slug needs a delegated token with the `tiles:map`
    scope in `Authorization: Bearer`. `detail=full` adds the legend text and
    reference `/carto` carries (see `Detail`).
    """
    return await render_map_tile(
        request, background_tasks, slug, tile, cache, credentials, detail
    )


@legacy_router.get("/{z:int}/{x:int}/{y:int}", **TILE_RESPONSE_PARAMS)
async def carto_tile(
    request: Request,
    background_tasks: BackgroundTasks,
    tile: Tile = Depends(TileParams),
    cache: CacheMode = CacheMode.prefer,
):
    """`/map/carto/{z}/{x}/{y}` under its previous address. Deprecated."""
    return await render_map_tile(request, background_tasks, "carto", tile, cache, None)


async def render_map_tile(
    request: Request,
    background_tasks: BackgroundTasks,
    slug: str,
    tile: Tile,
    cache: CacheMode,
    credentials: Optional[HTTPAuthorizationCredentials],
    detail: Detail = Detail.slim,
):
    # Before anything touches the database: an unauthenticated request for a
    # guarded slug costs nothing.
    if not is_public(slug):
        await _guard(request, credentials)

    pool = request.app.state.pool
    catalog = request.app.state.function_catalog

    if slug == LEGACY_CARTO:
        layer = catalog.get("carto-slim")

        async def get_tile(request: Request, args: CachedTileArgs):
            return await layer.get_tile(pool, args.tile)

    else:
        source = await _resolve(pool, slug, tile.z)
        if not _in_range(source, tile.z):
            return VectorTileResponse()
        if source["layer_id"] is not None:

            async def get_tile(request: Request, args: CachedTileArgs):
                q, p = render(
                    faces_sql(detail),
                    z=args.tile.z,
                    x=args.tile.x,
                    y=args.tile.y,
                    layer_id=source["layer_id"],
                )
                async with pool.acquire() as conn:
                    return await conn.fetchval(q, *p)

        else:
            layer = catalog.get("map")

            async def get_tile(request: Request, args: CachedTileArgs):
                return await layer.get_tile(
                    pool, args.tile, source_id=source["source_id"]
                )

    mode, profile_id = await _cache_for(pool, slug, cache, detail)
    args = CachedTileArgs(
        layer=profile_id,
        tile=tile,
        media_type=MimeTypes.pbf,
        params={},
        mode=mode,
    )
    return await handle_cached_tile_request(
        request, pool, background_tasks, get_tile, args
    )


async def _resolve(pool, slug: str, z: int) -> dict:
    q, p = render(_RESOLVE, slug=slug, z=z)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(q, *p)
    if row is None or row["source_id"] is None:
        raise HTTPException(404, f"No map or compilation matching '{slug}'")
    if row["is_served"] is False:
        raise HTTPException(404, f"'{slug}' is not served by name")
    return dict(row)


def _in_range(source: dict, z: int) -> bool:
    if source["min_zoom"] is not None and z < source["min_zoom"]:
        return False
    if source["max_zoom"] is not None and z > source["max_zoom"]:
        return False
    return True


@router.get("/{slug}/tilejson.json")
async def map_tilejson(request: Request, slug: str):
    """TileJSON for any served source: its tile URL, bounds and zoom range.

    Unguarded, since it says only where and at which zooms a source is drawn;
    the tiles themselves keep their access rule.
    """
    q, p = render(_DESCRIBE, slug=slug)
    async with request.app.state.pool.acquire() as conn:
        row = await conn.fetchrow(q, *p)
    if row is None:
        raise HTTPException(404, f"No map or compilation matching '{slug}'")
    if row["is_served"] is False:
        raise HTTPException(404, f"'{slug}' is not served by name")

    base = str(request.base_url).rstrip("/")
    tiles = f"{base}/map/{quote(row['slug'], safe='')}/{{z}}/{{x}}/{{y}}"

    bounds = [-180, -90, 180, 90]
    if row["west"] is not None:
        bounds = [row["west"], row["south"], row["east"], row["north"]]

    minzoom = row["min_zoom"]
    if minzoom is None:
        minzoom = DEFAULT_MINZOOM
    maxzoom = row["max_zoom"]
    if maxzoom is None:
        maxzoom = DEFAULT_MAXZOOM

    doc = {
        "tilejson": "3.0.0",
        "name": row["name"] or row["slug"],
        "tiles": [tiles],
        "bounds": bounds,
        "minzoom": minzoom,
        "maxzoom": maxzoom,
        "vector_layers": [{"id": "units", "fields": {}}, {"id": "lines", "fields": {}}],
    }
    # Bounds too large to see at the minimum zoom -- a compilation spanning a
    # continent, drawn only from a medium-scale zoom -- get a center to open at
    # instead, where the map is actually drawn.
    if row["center_lng"] is not None and not _fits(bounds, minzoom):
        doc["center"] = [row["center_lng"], row["center_lat"], minzoom]
    # Not TileJSON's own: the solved faces of a compilation, which say which
    # maps it resolves to at every zoom, including those it draws no units at.
    if row["has_faces"]:
        doc["faces"] = (
            f"{base}/dev/topology/faces/{quote(row['slug'], safe='')}/{{z}}/{{x}}/{{y}}"
        )
    return doc


def _fits(bounds: list[float], zoom: int) -> bool:
    span = 360 / 2**zoom * VIEW_TILES
    west, south, east, north = bounds
    return east - west <= span and north - south <= span


# Profiles that were asked for but do not exist, so the warning is logged once.
_missing_profiles: set[str] = set()


async def _cache_for(
    pool, slug: str, requested: CacheMode, detail: Detail = Detail.slim
) -> tuple[CacheMode, int]:
    """Whether this request may use the tile cache, and under which profile.

    A slug without a profile is never cached. A profile that is declared here
    but missing from `tile_cache.profile` degrades to no cache rather than
    failing the tile, since the row is seed data a database may lag on.
    """
    profile = cache_profile(slug, detail)
    if profile is None or requested == CacheMode.bypass:
        return CacheMode.bypass, -1
    try:
        return requested, await get_layer_id(pool, profile)
    except ValueError:
        if profile not in _missing_profiles:
            _missing_profiles.add(profile)
            log.warning(
                "Tile cache profile %s is not in tile_cache.profile; serving %s uncached",
                profile,
                slug,
            )
        return CacheMode.bypass, -1
