import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

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


if __name__ == "__main__":
    asyncio.run(insert())
