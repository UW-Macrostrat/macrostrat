import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)


async def connect_engine():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT * FROM macrostrat.intervals LIMIT 1"))
        rows = result.fetchall()
        if not rows:
            print("No rows found in macrostrat.intervals.")
        else:
            print("Rows found in macrostrat.intervals:", rows)


if __name__ == "__main__":
    asyncio.run(connect_engine())
