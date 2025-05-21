from ctypes import c_int32
from json import dumps

from buildpg import asyncpg, render
from contextvars import ContextVar
from enum import Enum
from hashlib import md5
from macrostrat.utils import get_logger
from morecantile import Tile
from pydantic import BaseModel
from typing import Optional, Union

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


class CacheArgs(BaseModel):
    layer: Union[int, str]
    tile: Tile
    media_type: str
    params: Optional[dict[str, str]] = None
    tms: str = "WebMercatorQuad"
    mode: CacheMode = CacheMode.prefer


async def get_cached_tile(
    pool: asyncpg.BuildPgPool,
    args: CacheArgs,
) -> Optional[bytes]:
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

        return await conn.fetchval(q, *p)


async def get_layer_id(pool, layer):
    """Get the layer ID from the database"""
    if isinstance(layer, int):
        return layer

    return await get_cache_profile_id(pool, layer)


async def set_cached_tile(
    pool: asyncpg.BuildPgPool,
    args: CacheArgs,
    content: bytes,
):

    tile = args.tile

    layer_id = await get_layer_id(pool, args.layer)

    async with pool.acquire() as conn:
        q, p = render(
            prepared_statement("set-cached-tile"),
            x=tile.x,
            y=tile.y,
            z=tile.z,
            params=create_params_hash(args.params),
            tile=content,
            profile=layer_id,
        )
        await conn.execute(q, *p)


profiles = ContextVar("profiles", default={})


async def get_cache_profile_id(pool: asyncpg.BuildPgPool, name: str):
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
