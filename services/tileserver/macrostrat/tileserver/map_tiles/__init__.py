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

from pathlib import Path
from typing import Optional

from buildpg import render
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from morecantile import Tile

from macrostrat.tileserver_utils import (
    CachedTileArgs,
    CacheMode,
    MimeTypes,
    TileParams,
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
# id as text; `serving_source` is the multiscale hop. A name that matches
# nothing comes back as a NULL `source_id`.
_RESOLVE = """
SELECT
  t.source_id,
  ml.id AS layer_id,
  map_bounds.is_served(t.source_id) AS is_served
FROM map_bounds.serving_source(map_bounds.resolve_source(:slug), :z) AS t(source_id)
LEFT JOIN map_bounds.map_layer ml ON ml.source_id = t.source_id
"""

_FACES_SQL = get_sql(__here__ / "queries" / "faces.sql")


def is_public(slug: str) -> bool:
    return slug in PUBLIC_SLUGS


def cache_profile(slug: str) -> Optional[str]:
    return CACHE_PROFILES.get(slug)


@router.get("/{slug}/{z:int}/{x:int}/{y:int}", **TILE_RESPONSE_PARAMS)
async def map_tile(
    request: Request,
    background_tasks: BackgroundTasks,
    slug: str,
    tile: Tile = Depends(TileParams),
    cache: CacheMode = CacheMode.prefer,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    """A tile of any source: a map, a compilation, or `carto` itself.

    `slug` is a source slug or an integer id. `carto` and `sys:carto-legacy`
    are public; every other slug needs a delegated token with the `tiles:map`
    scope in `Authorization: Bearer`.
    """
    return await render_map_tile(
        request, background_tasks, slug, tile, cache, credentials
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
        if source["layer_id"] is not None:

            async def get_tile(request: Request, args: CachedTileArgs):
                q, p = render(
                    _FACES_SQL,
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

    mode, profile_id = await _cache_for(pool, slug, cache)
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


# Profiles that were asked for but do not exist, so the warning is logged once.
_missing_profiles: set[str] = set()


async def _cache_for(pool, slug: str, requested: CacheMode) -> tuple[CacheMode, int]:
    """Whether this request may use the tile cache, and under which profile.

    A slug without a profile is never cached. A profile that is declared here
    but missing from `tile_cache.profile` degrades to no cache rather than
    failing the tile, since the row is seed data a database may lag on.
    """
    profile = cache_profile(slug)
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
