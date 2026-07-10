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


def get_engine(request: Request) -> AsyncEngine:
    """FastAPI dependency returning the process-wide async engine.

    The engine (and its connection pool) is created once in the app lifespan and
    stored on ``app.state`` — see ``api/app.py``. Handlers must receive it via
    injection rather than creating their own, which is what previously leaked a
    pool per request and exhausted Postgres connections.
    """
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise RuntimeError("Async engine not initialized; check the app lifespan")
    return engine


def get_db_url():
    # Try several options ot get a database URL
    # - MACROSTRAT_DATABASE_URL is used by PyTest embedded in the macrostrat cli
    # - uri is how the Postgres Operator passes
    # - DB_URL is nicer for .env files
    for env in ["MACROSTRAT_DATABASE_URL", "uri", "DB_URL"]:
        if environ.get(env, None) is not None:
            return environ.get(env)
    raise ValueError("No database URL found")


def get_sync_database(request: Request) -> Iterator[Database]:
    """FastAPI dependency yielding the process-wide synchronous ``Database``.

    Like the async engine, this is built once in the app lifespan and stored on
    ``app.state`` so every request shares one connection pool.

    ``Database.run_query`` leaves the thread-local session's transaction open
    (it never advances its internal generator to the commit), which keeps a
    connection checked out. Now that the pool is shared across all requests
    rather than recreated per request, that would exhaust the pool — so we
    release the scoped session here once the request finishes, returning its
    connection to the pool.
    """
    sync_db = getattr(request.app.state, "sync_db", None)
    if sync_db is None:
        raise RuntimeError("Sync database not initialized; check the app lifespan")
    try:
        yield sync_db
    finally:
        sync_db.session.remove()


# Pool configuration shared by the async engine and the sync Database. A single
# engine/pool is created per process in the app lifespan; ``pool_pre_ping``
# recycles connections dropped by the server instead of raising on first use.
_POOL_KWARGS = dict(
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)


def build_async_engine() -> AsyncEngine:
    """Build the async engine. Call once, in the app lifespan."""
    db_url = get_db_url()
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return create_async_engine(db_url, **_POOL_KWARGS)


def build_sync_database() -> Database:
    """Build the sync Database. Call once, in the app lifespan."""
    return Database(get_db_url(), **_POOL_KWARGS)


EngineDep = Annotated[AsyncEngine, Depends(get_engine)]
SyncDatabaseDep = Annotated[Database, Depends(get_sync_database)]


def get_async_session(
    engine: AsyncEngine, **kwargs
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, **kwargs)


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


async def insert_access_token(
    engine: AsyncEngine,
    token: str,
    group_id: int,
    expiration: datetime.datetime,
    token_type: str = "api",
):
    async with engine.begin() as conn:
        q = insert(schemas.Token).values(
            token=token,
            expires_on=expiration,
            group=group_id,
            token_type=token_type,
        )
        result = await conn.execute(q)
        return result


async def get_access_token(async_session: async_sessionmaker[AsyncSession], token: str):
    async with async_session() as session:
        select_stmt = select(schemas.Token).where(
            schemas.Token.token == token,
            schemas.Token.token_type == "api",
        )

        result = (await session.scalars(select_stmt)).first()
        if result is None:
            return None

        if result.expires_on < datetime.datetime.now(datetime.timezone.utc):
            return None

        stmt = (
            update(schemas.Token)
            .where(schemas.Token.id == result.id)
            .values(used_on=datetime.datetime.utcnow())
        )
        await session.execute(stmt)
        await session.commit()

        return result


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
