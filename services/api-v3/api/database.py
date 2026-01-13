#
# File of all db accesses
#
# When they can be they are made with the SQLAlchemy ORM model
#
# On the bottom you will find the methods that do not use this method
#
import datetime
from os import environ
from typing import Literal, Type

import api.schemas as schemas
from api.query_parser import QueryParser
from dotenv import load_dotenv
from pydantic import BaseModel
from sqlalchemy import CursorResult, MetaData, Table, func, insert, select, text, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from macrostrat.database import Database

load_dotenv()

engine: AsyncEngine | None = None
sync_db: Database | None = None


def get_engine() -> AsyncEngine:
    if engine is None:
        raise RuntimeError("Database engine not initialized yet")
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


def get_sync_database():
    global sync_db
    if sync_db is None:
        sync_db = Database(get_db_url())
    return sync_db


async def connect_engine() -> AsyncEngine:
    # Check the uri and DB_URL for the database connection string
    # uri is how the Postgres Operator passes, DB_URL is nicer for .env files
    global engine
    db_url = get_db_url()
    # Make sure this is all run async
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(db_url)
    return engine


async def dispose_engine():
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None


def get_async_session(
    engine: AsyncEngine, **kwargs
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, **kwargs)


async def source_id_to_slug(async_engine: AsyncEngine, source_id: id):
    async with get_async_session(async_engine)() as session:
        stmt = select(schemas.Sources).where(schemas.Sources.source_id == source_id)
        result = await session.scalar(stmt)

        if result is None:
            raise NoResultFound(
                f"Could not find primary_table corresponding with source_id: {source_id}"
            )

        return result.slug


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

async def insert_refresh_token(
    engine: AsyncEngine,
    token: str,
    group_id: int,
    expiration: datetime.datetime,
    token_type: str = "refresh",
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


async def get_refresh_token(async_session: async_sessionmaker[AsyncSession], token: str):
    async with async_session() as session:
        select_stmt = select(schemas.Token).where(
            schemas.Token.token == token,
            schemas.Token.token_type == "refresh",
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
    table_slug = await source_id_to_slug(get_engine(), table_id)
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
