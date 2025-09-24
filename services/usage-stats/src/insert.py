import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

raw_url = os.getenv("DATABASE_URL")

# Ensure it uses asyncpg
if raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    raise ValueError(
        "Invalid DATABASE_URL: must start with postgresql:// or postgresql+asyncpg://"
    )

DATABASE_URL = raw_url

engine = create_async_engine(DATABASE_URL, echo=True)


async def insert(payload=None, table_name=None):
    async with engine.connect() as conn:
        if payload is None:
            print("No payload provided")
            return

        if table_name is None:
            print("No table name provided")
            return

        if table_name not in ["macrostrat", "rockd"]:
            print("Invalid table name provided")
            return

        result = await conn.execute(
            text(
                f"""
            INSERT INTO usage_stats.{table_name}_stats 
                (lat, lng, date, ip, matomo_id) 
            VALUES (:lat, :lng, :date, :ip, :matomo_id)
        """
            ),
            (payload),
        )
        await conn.commit()
