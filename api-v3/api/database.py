from os import environ

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker

from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

INTEGRATION_DATABASE_URL = environ.get("DB_URL", None)

meta = MetaData()

engine: AsyncEngine = None


def get_engine():
    return engine


async def connect_engine() -> AsyncEngine:
    global engine
    engine = create_async_engine(INTEGRATION_DATABASE_URL)


async def dispose_engine():
    global engine
    await engine.dispose()


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




async def get_schema_tables(engine: AsyncEngine, schema: str):
    async with engine.begin() as conn:

        q = text("SELECT table_name FROM information_schema.tables WHERE table_schema = :schema")
        params = {"schema": schema}
        q = q.bindparams(**params)

        result = await conn.execute(q)

        return map(lambda x: x[0], result.fetchall())


async def select_table(engine: AsyncEngine, table: str, offset: int = 0, page_size: int = 100) -> SQLResponse:

    # Check that the table is a valid table source
    sources = await get_schema_tables(engine, 'sources')
    if table not in sources:
        raise Exception(f"Selected source table is not in the sources schema: {table}")


    async with engine.begin() as conn:
        await conn.run_sync(meta.create_all)

        result = await conn.execute(
            text(f"SELECT * FROM sources.{table} LIMIT :limit OFFSET :offset"),
            {
                "table": table,
                "limit": page_size,
                "offset": offset
            }
        )

        response = SQLResponse(result.keys(), result.fetchall())

        return response
