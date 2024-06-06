from typing import Optional

from buildpg import asyncpg, render
from morecantile import Tile
from hashlib import md5
from json import dumps

from .utils import prepared_statement


async def get_tile_from_cache(
    pool: asyncpg.BuildPgPool,
    layer: str,
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
    layer: str,
    params: dict[str, str],
    tile: Tile,
    content: bytes,
):
    async with pool.acquire() as conn:
        q, p = render(
            prepared_statement("set-cached-tile"),
            x=tile.x,
            y=tile.y,
            z=tile.z,
            params=create_params_hash(params),
            tile=content,
            profile=layer,
        )
        await conn.execute(q, *p)


def create_params_hash(params: dict[str, str]) -> str:
    """Create a hash from the params."""
    return md5(dumps(params, sort_keys=True).encode()).digest()
