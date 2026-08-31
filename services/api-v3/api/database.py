#
# File of all db accesses
#
# When they can be they are made with the SQLAlchemy ORM model
#
# On the bottom you will find the methods that do not use this method
#
import datetime
from os import environ
from typing import Annotated, Iterator, Literal, Type

import api.schemas as schemas
from api.query_parser import QueryParser
from dotenv import load_dotenv
from fastapi import Depends, Request
from pydantic import BaseModel
from sqlalchemy import CursorResult, MetaData, Table, func, insert, select, text, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from macrostrat.database import Database

load_dotenv()


def get_db_url():
    # Try several options ot get a database URL
    # - MACROSTRAT_DATABASE_URL is used by PyTest embedded in the macrostrat cli
    # - uri is how the Postgres Operator passes
    # - DB_URL is nicer for .env files
    for env in ["MACROSTRAT_DATABASE_URL", "uri", "DB_URL"]:
        if environ.get(env, None) is not None:
            return environ.get(env)
    raise ValueError("No database URL found")


# Pool configuration shared by the async engine and the sync database. A single
# engine/pool is created per process in the app lifespan; ``pool_pre_ping``
# recycles connections dropped by the server instead of raising on first use.
_POOL_KWARGS = dict(
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)


class AppDatabase:
    """Application-scoped async + sync connection pool manager, one per process.

    Pure integration sugar: it owns a SQLAlchemy async engine and the sync
    ``macrostrat.database.Database`` and exposes parallel accessors so route
    handlers can obtain whichever context they need — an async session/connection
    or the sync database — from the app/request scope in a standard way. It is
    *not* meant to be threaded into utility functions; those should take a
    concrete sync or async context (an engine, sessionmaker, connection, or the
    sync ``Database``) instead. Built once in the app lifespan and shared via
    ``app.state.db`` — see ``api/app.py``.
    """

    def __init__(self, url: str):
        async_url = url
        if async_url.startswith("postgresql://"):
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        self.async_engine: AsyncEngine = create_async_engine(async_url, **_POOL_KWARGS)
        # expire_on_commit=False keeps ORM objects usable after commit (the
        # recommended async default) so handlers can return them post-commit.
        self.async_sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.async_engine, expire_on_commit=False
        )
        self.sync: Database = Database(url, **_POOL_KWARGS)

    # --- async accessors ---
    def async_session(self, **kwargs) -> AsyncSession:
        """A fresh ``AsyncSession`` context manager: ``async with db.async_session() as s``."""
        return self.async_sessionmaker(**kwargs)

    def async_connection(self):
        """A transactional ``AsyncConnection`` context manager (``engine.begin()``)."""
        return self.async_engine.begin()

    # --- sync accessors ---
    @property
    def sync_engine(self):
        return self.sync.engine

    def sync_session(self):
        """A transactional sync ``Session`` context manager."""
        return self.sync.session_scope()

    def sync_connection(self):
        """A transactional sync ``Connection`` context manager (``engine.begin()``)."""
        return self.sync.engine.begin()

    async def dispose(self):
        """Dispose both connection pools. Call once, on app shutdown."""
        await self.async_engine.dispose()
        self.sync.engine.dispose()


def get_database(request: Request) -> Iterator[AppDatabase]:
    """FastAPI dependency yielding the process-wide ``AppDatabase``.

    The sync ``run_query`` helper leaves its thread-local session's transaction
    open (it never advances its internal generator to the commit), keeping a
    connection checked out. Since the pool is shared across all requests, we
    release the scoped session when the request finishes so its connection
    returns to the pool.
    """
    database = getattr(request.app.state, "db", None)
    if database is None:
        raise RuntimeError("Database not initialized; check the app lifespan")
    try:
        yield database
    finally:
        database.sync.session.remove()


DatabaseDep = Annotated[AppDatabase, Depends(get_database)]


async def source_id_to_slug(conn: AsyncConnection, source_id: int):
    """Look up a source's slug, reusing an existing connection.

    Takes a live connection rather than the engine so callers that already hold
    one (e.g. ``get_table``) don't acquire a second pooled connection while the
    first is still checked out.
    """
    stmt = select(schemas.Sources.slug).where(schemas.Sources.source_id == source_id)
    slug = (await conn.execute(stmt)).scalar()

    if slug is None:
        raise NoResultFound(
            f"Could not find primary_table corresponding with source_id: {source_id}"
        )

    return slug


async def get_sources(
    async_session: async_sessionmaker[AsyncSession], page: int = 0, page_size: int = 100
):
    async with async_session() as session:
        stmt = (
            select(schemas.Sources)
            .offset(page_size * page)
            .limit(page_size)
            .order_by(schemas.Sources.source_id)
        )
        result = await session.scalars(stmt)

        return [*result]


async def get_schema_tables(engine: AsyncEngine, schema: str):
    async with engine.begin() as conn:
        q = text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = :schema"
        )
        params = {"schema": schema}
        q = q.bindparams(**params)

        result = await conn.execute(q)

        return map(lambda x: x[0], result.fetchall())


async def insert_token(
    engine: AsyncEngine,
    *,
    token_hash: str,
    expires_on: datetime.datetime,
    token_type: str = "api",
    user_id: int | None = None,
    created_by: int | None = None,
    label: str | None = None,
    scopes: list[str] | None = None,
) -> int:
    """Store an issued token into the macrostrat_auth.token table and return its id.

    `token_hash` is the sha256 digest of the token, from `api.routes.security.hash_token`.
     The token must be associated to a macrostrat user_id (created when a user creates a macrostrat
     orcid account) or a label (assigned when generating
     a delegated 3rd party token). This is enforced by the `token_has_subject` check constraint in the db.
    """
    async with engine.begin() as conn:
        q = (
            insert(schemas.Token)
            .values(
                token=token_hash,
                expires_on=expires_on,
                token_type=token_type,
                user_id=user_id,
                created_by=created_by,
                label=label,
                scopes=scopes,
            )
            .returning(schemas.Token.id)
        )
        result = await conn.execute(q)
        return result.scalar_one()


async def get_token_by_hash(
    async_session: async_sessionmaker[AsyncSession],
    token_hash: str,
    token_type: str | None = None,
) -> schemas.Token | None:
    """Look up a live token by its sha256 digest, or None if absent/expired.

    Pass `token_type` to restrict the lookup to one kind of token; omit it to
    accept any. Touches `used_on` on a hit, so this is not suitable for
    high-volume callers (tile requests) — those should read without the write.
    """
    async with async_session() as session:
        select_stmt = select(schemas.Token).where(schemas.Token.token == token_hash)
        if token_type is not None:
            select_stmt = select_stmt.where(schemas.Token.token_type == token_type)

        result = (await session.scalars(select_stmt)).first()
        if result is None:
            return None

        if result.expires_on < datetime.datetime.now(datetime.timezone.utc):
            return None

        stmt = (
            update(schemas.Token)
            .where(schemas.Token.id == result.id)
            .values(used_on=datetime.datetime.now(datetime.timezone.utc))
        )
        await session.execute(stmt)
        await session.commit()

        return result


async def get_role_id(
    async_session: async_sessionmaker[AsyncSession], name: str
) -> int | None:
    """Resolve a role name to its id. Roles are seeded by the schema."""
    async with async_session() as session:
        return await session.scalar(
            select(schemas.Role.id).where(schemas.Role.name == name)
        )


#
# Here starts the use on the engine object directly
#


def results_to_model(results, model: Type[BaseModel]) -> list[BaseModel]:
    """Converts the results to a list of models"""

    keys = list(results.keys())
    return [
        model(**{keys[i]: result[i] for i, v in enumerate(result)})
        for result in results.fetchall()
    ]


class SQLResponse:
    def __init__(self, columns, results):
        self.columns = list(columns)
        self.results = results

    def to_dict(self):
        """Converts the response to the 'record' format list"""

        l = []
        for result in self.results:
            d = {}
            for i, v in enumerate(result):
                d[self.columns[i]] = result[i]

            l.append(d)

        return l


async def get_table(
    conn, table_id: int, geometry_type: Literal["polygons", "points", "lines"]
) -> Table:
    metadata = MetaData(schema="sources")
    table_slug = await source_id_to_slug(conn, table_id)
    table_name = f"{table_slug}_{geometry_type}"
    table = await conn.run_sync(
        lambda sync_conn: Table(table_name, metadata, autoload_with=sync_conn)
    )
    return table


async def get_sources_sub_table_count(
    engine: AsyncEngine,
    table_id: int,
    geometry_type: Literal["polygons", "points", "lines"],
    query_params: list = None,
) -> int:
    async with engine.begin() as conn:
        table = await get_table(conn, table_id, geometry_type)

        # Extract filters from the query parameters
        query_parser = QueryParser(columns=table.columns, query_params=query_params)

        stmt = None
        if query_parser.get_group_by_column() is not None:
            sub_stmt = (
                select(query_parser.get_group_by_column())
                .where(query_parser.where_expressions())
                .group_by(query_parser.get_group_by_column())
            )

            stmt = select(func.count("*")).select_from(sub_stmt)
        else:
            stmt = (
                select(func.count())
                .select_from(table)
                .where(query_parser.where_expressions())
            )

        x = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        result = await conn.execute(stmt)

        return result.scalar()


async def select_sources_sub_table(
    engine: AsyncEngine,
    table_id: int,
    geometry_type: Literal["polygons", "points", "lines"],
    page: int = 0,
    page_size: int = 100,
    query_params: list = None,
) -> SQLResponse:
    async with engine.begin() as conn:
        table = await get_table(conn, table_id, geometry_type)

        # Strip out the unwanted columns
        ignored_columns = [
            "geom",
            "geometry",
        ]  # No reason that this moment to pass this through
        selected_columns = table.c[
            *[col.key for col in table.c if col.key not in ignored_columns]
        ]

        # Extract filters from the query parameters
        query_parser = QueryParser(columns=selected_columns, query_params=query_params)
        if query_parser.get_group_by_column() is not None:
            selected_columns = query_parser.get_select_columns()

        stmt = (
            select(*selected_columns)
            .order_by(*query_parser.get_order_by_columns())
            .limit(page_size)
            .offset(page_size * page)
            .where(query_parser.where_expressions())
        )

        if query_parser.get_group_by_column() is not None:
            stmt = stmt.group_by(query_parser.get_group_by_column()).order_by(
                query_parser.get_group_by_column()
            )

        x = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        result = await conn.execute(stmt)

        response = SQLResponse(result.keys(), result.fetchall())

        return response


async def patch_sources_sub_table(
    engine: AsyncEngine,
    table_id: int,
    geometry_type: Literal["polygons", "points", "lines"],
    update_values: dict,
    query_params: list = None,
) -> CursorResult:
    async with engine.begin() as conn:
        table = await get_table(conn, table_id, geometry_type)

        # Extract filters from the query parameters
        query_parser = QueryParser(columns=table.columns, query_params=query_params)

        stmt = (
            update(table)
            .where(query_parser.where_expressions())
            .values(**update_values)
        )

        x = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        result = await conn.execute(stmt)

        return result


async def patch_sources_sub_table_set_columns_equal(
    engine: AsyncEngine,
    table_id: int,
    geometry_type: Literal["polygons", "points", "lines"],
    target_column: str,
    source_column: str,
    query_params: list = None,
) -> CursorResult:
    async with engine.begin() as conn:
        table = await get_table(conn, table_id, geometry_type)

        # Extract filters from the query parameters
        query_parser = QueryParser(columns=table.columns, query_params=query_params)

        stmt = (
            update(table)
            .where(query_parser.where_expressions())
            .values({getattr(table.c, target_column): getattr(table.c, source_column)})
        )

        result = await conn.execute(stmt)

        return result
