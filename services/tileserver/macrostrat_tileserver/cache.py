from typing import Optional

from buildpg import asyncpg, render
from morecantile import Tile

from .utils import prepared_statement


async def get_tile_from_cache(
    pool: asyncpg.BuildPgPool, layer: str, tile: Tile, tms: str = "WebMercatorQuad"
) -> Optional[bytes]:
    """Get tile data from cache."""
    # Get the tile from the tile_cache.tile table
    async with pool.acquire() as conn:
        q, p = render(
            prepared_statement("get-cached-tile"),
            x=tile.x,
            y=tile.y,
            z=tile.z,
            tms=tms,
            layer=layer,
        )

        return await conn.fetchval(q, *p)


async def set_cached_tile(
    pool: asyncpg.BuildPgPool, layer: str, tile: Tile, content: bytes
):
    async with pool.acquire() as conn:
        q, p = render(
            prepared_statement("set-cached-tile"),
            x=tile.x,
            y=tile.y,
            z=tile.z,
            tile=content,
            layers=[layer],
            profile=layer,
        )
        await conn.execute(q, *p)
