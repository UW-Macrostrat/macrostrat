import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

raw_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/dbname")

# Ensure it uses asyncpg
if raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif not raw_url.startswith("postgresql+asyncpg://"):
    raise ValueError(
        "Invalid DATABASE_URL: must start with postgresql:// or postgresql+asyncpg://"
    )

DATABASE_URL = raw_url

engine = create_async_engine(DATABASE_URL, echo=True)


async def get_last_id(table_name=None):
    async with engine.connect() as conn:
        if table_name is None:
            print("No table name provided")
            return

        print("Fetching data")

        result = await conn.execute(
            text(f"SELECT MAX(matomo_id) FROM usage_stats.{table_name}_stats")
        )
        rows = result.fetchall()
        id = rows[0][0]

        # Note: If you want to regenerate the table, truncate it first, then
        # this script will repopulate it automatically.

        # Check if table is empty
        if not id:
            return 0
        else:
            return id
