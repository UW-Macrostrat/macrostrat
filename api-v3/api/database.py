#
# File of all db accesses
#
# When they can be they are made with the SQLAlchemy ORM model
#
# On the bottom you will find the methods that do not use this method
#

from os import environ
from typing import Type

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import text, select, update, Table, MetaData, CursorResult
from sqlalchemy.exc import NoResultFound, NoSuchTableError

from dotenv import load_dotenv

import api.schemas as schemas

load_dotenv()

INTEGRATION_DATABASE_URL = environ.get("DB_URL", None)

engine: AsyncEngine = None


def get_engine():
    return engine


async def connect_engine() -> AsyncEngine:
    global engine
    engine = create_async_engine(INTEGRATION_DATABASE_URL)


async def dispose_engine():
    global engine
    await engine.dispose()


def get_async_session(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine)


async def source_id_to_primary_table(async_session: async_sessionmaker[AsyncSession], source_id: id):
    async with async_session() as session:
        stmt = select(schemas.Sources).where(schemas.Sources.source_id == source_id)
        result = await session.scalar(stmt)

        if result is None:
            raise NoResultFound(f"Could not find primary_table corresponding with source_id: {source_id}")

        return result.primary_table


async def get_sources(async_session: async_sessionmaker[AsyncSession], page: int = 1, page_size: int = 100):
    async with async_session() as session:
        stmt = select(schemas.Sources).offset(page_size * (page - 1)).limit(page_size).order_by(schemas.Sources.source_id)
        result = await session.scalars(stmt)

        return [*result]


async def get_schema_tables(engine: AsyncEngine, schema: str):
    async with engine.begin() as conn:

        q = text("SELECT table_name FROM information_schema.tables WHERE table_schema = :schema")
        params = {"schema": schema}
        q = q.bindparams(**params)

        result = await conn.execute(q)

        return map(lambda x: x[0], result.fetchall())


#
# Here starts the use on the engine object directly
#

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


async def select_sources_sub_table(engine: AsyncEngine, table_id: int, offset: int = 0, page_size: int = 100, column_expression= None) -> SQLResponse:

    # Check that the table is a valid table source
    session = get_async_session(engine)
    try:
        primary_table = await source_id_to_primary_table(session, table_id)
        polygon_table = f"{primary_table}_polygons"
    except NoResultFound as e:
        raise NoSuchTableError(e)

    async with engine.begin() as conn:

        metadata = MetaData(schema="sources")
        table = await conn.run_sync(lambda sync_conn: Table(polygon_table, metadata, autoload_with=sync_conn))

        ignored_columns = ['geom', 'db_id']  # No reason that this moment to pass this through
        selected_columns = table.c[*[col.key for col in table.c if col.key not in ignored_columns]]

        stmt = select(selected_columns)\
            .limit(page_size)\
            .offset(offset)\
            .where(column_expression)

        result = await conn.execute(stmt)

        response = SQLResponse(result.keys(), result.fetchall())

        return response

async def patch_sources_sub_table(engine: AsyncEngine, table_id: int, update_values, column_expression=None) -> CursorResult:

    # Check that the table is a valid table source
    session = get_async_session(engine)
    try:
        primary_table = await source_id_to_primary_table(session, table_id)
        polygon_table = f"{primary_table}_polygons"
    except NoResultFound as e:
        raise NoSuchTableError(e)

    async with engine.begin() as conn:

        metadata = MetaData(schema="sources")

        # Grabbing a table from the database as it is
        table = await conn.run_sync(lambda sync_conn: Table(polygon_table, metadata, autoload_with=sync_conn))

        stmt = update(table).where(column_expression).values(**update_values)

        x = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        result = await conn.execute(stmt)

        return result