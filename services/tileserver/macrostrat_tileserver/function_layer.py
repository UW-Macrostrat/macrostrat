import json
from typing import Any, Dict, List, Optional

import morecantile
from buildpg import Func
from buildpg import asyncpg, clauses, render

from timvt.errors import (
    MissingEPSGCode,
)
from timvt.settings import TileSettings
from timvt.layers import Function

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
                    ":xmin",
                    ":ymin",
                    ":xmax",
                    ":ymax",
                    ":epsg",
                    ":query_params::text::json",
                ),
            )
            q, p = render(
                str(sql_query),
                xmin=bbox.left,
                ymin=bbox.bottom,
                xmax=bbox.right,
                ymax=bbox.top,
                epsg=tms.crs.to_epsg(),
                query_params=json.dumps(kwargs),
            )

            # execute the query
            content = await conn.fetchval(q, *p)

            # rollback
            await transaction.rollback()

        return content
