"""The synchronous engine shared by the raster and elevation routes.

Both read the `raster_layers` index from sync endpoints in Starlette's
threadpool. A default engine per route set let each worker hold up to 15
connections apiece, and with 16 workers that outgrew the database's
`max_connections`; one small engine per worker keeps them inside a budget.
"""

from functools import cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

__all__ = ["sync_engine"]


@cache
def sync_engine(url: str) -> Engine:
    """The worker's one engine for `url`; index lookups hold a connection only briefly."""
    return create_engine(
        url,
        pool_size=2,
        max_overflow=3,
        pool_timeout=10,
        # Patroni failovers leave stale connections in the pool.
        pool_pre_ping=True,
        connect_args={"application_name": "tileserver-rasters"},
    )
