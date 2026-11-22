"""Function-backed vector tile serving.

This replaces the vendored `timvt` fork. Macrostrat's tile layers are all stored
PostgreSQL functions returning MVT bytes, so this keeps only that: a registry of
layers, the tile and TileJSON routes, and the connection pool they run on.
Table reflection, tile-matrix-set negotiation, the OGC metadata endpoints and
the built-in viewer are gone — none were used.
"""

from .database import PostgresSettings, close_db_connection, connect_to_db
from .factory import (
    TILE_RESPONSE_PARAMS,
    VectorTileFactory,
    layer_dependency,
    queryparams_to_kwargs,
)
from .layers import FunctionRegistry, StoredFunction

__all__ = [
    "PostgresSettings",
    "connect_to_db",
    "close_db_connection",
    "VectorTileFactory",
    "TILE_RESPONSE_PARAMS",
    "queryparams_to_kwargs",
    "layer_dependency",
    "FunctionRegistry",
    "StoredFunction",
]
