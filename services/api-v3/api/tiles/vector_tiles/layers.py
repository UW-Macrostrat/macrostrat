"""Vector-tile layers backed by stored SQL functions.

Every layer Macrostrat serves is a PostgreSQL function of `(x, y, z, params)`
returning MVT bytes, so that is the only layer type this supports — no table
reflection, no per-layer SQL, no tile-matrix negotiation. Replaces
`timvt.layer`.
"""

import json
from typing import Any, Optional

from buildpg import Func, asyncpg, clauses, render
from morecantile import Tile

from macrostrat.utils import get_logger

log = get_logger(__name__)

__all__ = ["StoredFunction", "FunctionRegistry"]

# Every layer is served on this grid; the tile server has never offered another,
# and the SQL functions assume it (they call ST_TileEnvelope directly).
DEFAULT_TMS = "WebMercatorQuad"


class StoredFunction:
    """A layer served by a stored function taking `(x, y, z, query_params)`.

    `id` is the layer's public name — the function name with its schema stripped
    and underscores hyphenated, e.g. `tile_layers.carto_slim` → `carto-slim`.
    """

    type: str = "StoredFunction"

    # Name of the tile-cache profile to use; None means "don't cache this layer".
    profile_id: Optional[str] = None

    bounds: list[float] = [-180, -90, 180, 90]
    minzoom: int = 0
    maxzoom: int = 22
    default_tms: str = DEFAULT_TMS

    def __init__(self, function_name: str):
        self.function_name = function_name
        name = function_name.split(".")[-1]
        self.id = name.replace("_", "-")

    def __repr__(self):
        return f"<{type(self).__name__} {self.id} → {self.function_name}>"

    def render_query(self, tile: Tile, **kwargs: Any):
        """Build the `SELECT function(x, y, z, params)` call for a tile."""
        sql_query = clauses.Select(
            Func(
                self.function_name,
                ":x",
                ":y",
                ":z",
                ":query_params::text::json",
            ),
        )
        return render(
            str(sql_query),
            x=tile.x,
            y=tile.y,
            z=tile.z,
            query_params=json.dumps(kwargs),
        )

    async def get_tile(self, pool: asyncpg.BuildPgPool, tile: Tile, **kwargs: Any):
        """Run the function and return the tile's MVT bytes.

        Wrapped in a transaction that is always rolled back: tile functions are
        read-only by contract, and rolling back means a function that
        accidentally writes can't corrupt anything.
        """
        query, params = self.render_query(tile, **kwargs)
        log.debug("Executing query: %s, %s", query, params)
        async with pool.acquire() as conn:
            transaction = conn.transaction()
            await transaction.start()
            content = await conn.fetchval(query, *params)
            await transaction.rollback()
        return content

    async def validate_request(self, pool, tile: Tile, **kwargs: Any):
        """Reject a request before it reaches the database.

        Overridden by layers with expensive or narrow parameter domains (see
        `PaleoGeographyLayer`). Raise `ValueError` to return a 400.
        """


class FunctionRegistry:
    """The layers an application serves, keyed by public layer name."""

    def __init__(self):
        self.funcs: dict[str, StoredFunction] = {}

    def get(self, key: str) -> Optional[StoredFunction]:
        return self.funcs.get(key)

    def register(self, *layers: StoredFunction) -> None:
        for layer in layers:
            self.funcs[layer.id] = layer

    def values(self):
        return self.funcs.values()

    def __contains__(self, key: str) -> bool:
        return key in self.funcs

    def __len__(self) -> int:
        return len(self.funcs)
