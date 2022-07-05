import json
from typing import Any, Dict, List, Optional

import morecantile
from buildpg import Func
from buildpg import asyncpg, clauses, render

from timvt.errors import (
    MissingEPSGCode,
)
from timvt.settings import TileSettings
from timvt.layer import Function

tile_settings = TileSettings()


class StoredFunction(Function):

    type: str = "StoredFunction"

    async def get_tile(
        self,
        pool: asyncpg.BuildPgPool,
        tile: morecantile.Tile,
        tms: morecantile.TileMatrixSet,
        **kwargs: Any,
    ):
        """Get Tile Data."""
        # We only support TMS with valid EPSG code
        if not tms.crs.to_epsg():
            raise MissingEPSGCode(
                f"{tms.identifier}'s CRS does not have a valid EPSG code."
            )

        bbox = tms.xy_bounds(tile)

        async with pool.acquire() as conn:
            transaction = conn.transaction()
            await transaction.start()

            # Build the query
            sql_query = clauses.Select(
                Func(
                    self.function_name,
                    ":x",
                    ":y",
                    ":z",
                    ":query_params::text::json",
                ),
            )
            q, p = render(
                str(sql_query),
                x=tile.x,
                y=tile.y,
                z=tile.z,
                query_params=json.dumps(kwargs),
            )

            # execute the query
            content = await conn.fetchval(q, *p)

            # rollback
            await transaction.rollback()

        return content
