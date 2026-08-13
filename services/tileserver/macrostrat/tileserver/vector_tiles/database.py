"""The asyncpg connection pool backing vector-tile routes.

Replaces `timvt.db`. Same shape — an app-scoped `buildpg` pool with JSON codecs
— minus the table-catalog reflection, which nothing here uses now that layers
are always stored functions.
"""

from typing import Optional

import orjson
from buildpg import asyncpg
from fastapi import FastAPI
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["PostgresSettings", "connect_to_db", "close_db_connection"]


class PostgresSettings(BaseSettings):
    """Connection and pool settings, read from the environment."""

    database_url: Optional[str] = None

    db_min_conn_size: int = 1
    db_max_conn_size: int = 10
    db_max_queries: int = 50000
    db_max_inactive_conn_lifetime: float = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


async def _init_connection(conn):
    """Decode json/jsonb with orjson rather than asyncpg's default."""
    await conn.set_type_codec(
        "json", encoder=orjson.dumps, decoder=orjson.loads, schema="pg_catalog"
    )
    await conn.set_type_codec(
        "jsonb", encoder=orjson.dumps, decoder=orjson.loads, schema="pg_catalog"
    )


async def connect_to_db(
    app: FastAPI, settings: Optional[PostgresSettings] = None, **kwargs
) -> None:
    """Open the pool and attach it to `app.state.pool`."""
    if settings is None:
        settings = PostgresSettings()

    app.state.pool = await asyncpg.create_pool_b(
        settings.database_url,
        min_size=settings.db_min_conn_size,
        max_size=settings.db_max_conn_size,
        max_queries=settings.db_max_queries,
        max_inactive_connection_lifetime=settings.db_max_inactive_conn_lifetime,
        init=_init_connection,
        **kwargs,
    )


async def close_db_connection(app: FastAPI) -> None:
    """Close the pool."""
    await app.state.pool.close()
