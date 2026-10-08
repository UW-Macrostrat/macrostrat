from contextvars import ContextVar
from ctypes import c_int32
from enum import Enum
from hashlib import md5
from json import dumps
from typing import Awaitable, Callable, NamedTuple, Optional, Union

from buildpg import asyncpg, render
from fastapi import BackgroundTasks, HTTPException, Request
from morecantile import Tile
from pydantic import BaseModel

from macrostrat.utils import CodeTimer, get_logger

from .output import TileResponse
from .utils import prepared_statement

log = get_logger(__name__)


class CacheMode(str, Enum):
    prefer = "prefer"
    force = "force"
    bypass = "bypass"


class CacheStatus(str, Enum):
    hit = "hit"
    miss = "miss"
    bypass = "bypass"


class CachedTileArgs(BaseModel):
    layer: Union[int, str]
    tile: Tile
    media_type: str
    params: Optional[dict[str, str]] = None
    tms: str = "WebMercatorQuad"
    mode: CacheMode = CacheMode.prefer


class RenderedTile(NamedTuple):
    """A tile's bytes and, when the renderer knows them, the maps it draws
    (`source_id`s). Both are cached, so a hit answers with the same header."""

    content: bytes
    sources: Optional[list[int]] = None


TileGetter = Callable[[Request, CachedTileArgs], Awaitable[Union[bytes, RenderedTile]]]


async def handle_cached_tile_request(
    request: Request,
    pool: asyncpg.BuildPgPool,
    background_tasks: BackgroundTasks,
    get_tile: TileGetter,
    args: CachedTileArgs,
) -> TileResponse:
    """Return vector tile."""
    timer = CodeTimer()

    # If cache is not bypassed and the tile is in the cache, return it
    if args.mode != CacheMode.bypass:
        cached = await get_cached_tile(pool, args)
        timer.step("check_cache")
        if cached is not None:
            return TileResponse(
                cached.content,
                timer,
                cache_status=CacheStatus.hit,
                sources=cached.sources,
                media_type=args.media_type,
            )

    # If the cache is forced and the tile is not in the cache, return a 404
    if args.mode == CacheMode.force:
        raise HTTPException(
            status_code=404,
            detail="Tile not found in cache",
            headers={
                "Server-Timing": timer.server_timings(),
                "X-Tile-Cache": CacheStatus.miss,
            },
        )

    rendered = await get_tile(request, args)
    if not isinstance(rendered, RenderedTile):
        rendered = RenderedTile(rendered)
    timer.step("get_tile")

    if args.mode != CacheMode.bypass:
        background_tasks.add_task(set_cached_tile, pool, args, rendered)

    return TileResponse(
        rendered.content,
        timer,
        cache_status=CacheStatus.miss,
        sources=rendered.sources,
        media_type=args.media_type,
    )


async def get_cached_tile(
    pool: asyncpg.BuildPgPool,
    args: CachedTileArgs,
) -> Optional[RenderedTile]:
    """Get tile data from cache."""
    # Get the tile from the tile_cache.tile table
    tile = args.tile

    layer_id = await get_layer_id(pool, args.layer)

    async with pool.acquire() as conn:
        q, p = render(
            prepared_statement("get-cached-tile"),
            x=tile.x,
            y=tile.y,
            z=tile.z,
            params=create_params_hash(args.params),
            tms=args.tms,
            layer=layer_id,
        )
        log.debug("Got cached tile: %s", tile)

        row = await conn.fetchrow(q, *p)
        if row is None:
            return None
        return RenderedTile(row["tile"], row["sources"])


async def set_cached_tile(
    pool: asyncpg.BuildPgPool,
    args: CachedTileArgs,
    rendered: Union[bytes, RenderedTile],
):
    if not isinstance(rendered, RenderedTile):
        rendered = RenderedTile(rendered)

    tile = args.tile

    layer_id = await get_layer_id(pool, args.layer)

    async with pool.acquire() as conn:
        q, p = render(
            prepared_statement("set-cached-tile"),
            x=tile.x,
            y=tile.y,
            z=tile.z,
            params=create_params_hash(args.params),
            tile=rendered.content,
            sources=rendered.sources,
            profile=layer_id,
        )
        await conn.execute(q, *p)


profiles = ContextVar("profiles", default={})


async def get_layer_id(pool, layer):
    """Get the layer ID from the database"""
    if isinstance(layer, int):
        return layer
    return await _get_cache_profile_id(pool, layer)


async def _get_cache_profile_id(pool: asyncpg.BuildPgPool, name: str):
    index = profiles.get()
    if name in index:
        return index[name]

    # Set the cache profile id from the database
    async with pool.acquire() as conn:
        q, p = render(
            "SELECT id FROM tile_cache.profile WHERE name = :layer",
            layer=name,
        )
        res = await conn.fetchval(q, *p)
        if res is None:
            raise ValueError(f"Cache profile {name} not found")
        # Store the result in the context variable
        index[name] = res
        profiles.set(index)

        return res


def create_params_hash(params) -> int:
    """Create a hash from the params, as an integer"""
    if params is None:
        return 0
    val = md5(dumps(params, sort_keys=True).encode()).hexdigest()
    # Restrict to 32 bits
    return c_int32(int(val, 16)).value
