from typing import Optional

from buildpg import asyncpg, render
from morecantile import Tile
from hashlib import md5
from json import dumps
from ctypes import c_int32

from .utils import prepared_statement

from macrostrat.utils import get_logger

log = get_logger(__name__)


async def get_tile_from_cache(
    pool: asyncpg.BuildPgPool,
    layer: int,
    params: dict[str, str],
    tile: Tile,
    tms: str = "WebMercatorQuad",
) -> Optional[bytes]:
    """Get tile data from cache."""
    # Get the tile from the tile_cache.tile table
    async with pool.acquire() as conn:
        q, p = render(
            prepared_statement("get-cached-tile"),
            x=tile.x,
            y=tile.y,
            z=tile.z,
            params=create_params_hash(params),
            tms=tms,
            layer=layer,
        )

        return await conn.fetchval(q, *p)


async def set_cached_tile(
    pool: asyncpg.BuildPgPool,
    layer: int,
    params: dict[str, str],
    tile: Tile,
    content: bytes,
):

    _hash = create_params_hash(params)
    log.debug("Setting cached tile: %s", _hash)

    async with pool.acquire() as conn:
        q, p = render(
            prepared_statement("set-cached-tile"),
            x=tile.x,
            y=tile.y,
            z=tile.z,
            params=_hash,
            tile=content,
            profile=layer,
        )
        await conn.execute(q, *p)


def create_params_hash(params) -> int:
    """Create a hash from the params, as an integer"""
    if params is None:
        return 0
    val = md5(dumps(params, sort_keys=True).encode()).hexdigest()
    # Restrict to 32 bits
    return c_int32(int(val, 16)).value
