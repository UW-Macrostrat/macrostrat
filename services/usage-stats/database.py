import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)

async def insert_rockd(payload=None):
    async with engine.connect() as conn:
        if payload is None:
            print("No payload provided")
            return
        
        print("Inserting payload", payload)

        result = await conn.execute(text("SELECT * FROM macrostrat.intervals LIMIT 1"))
        rows = result.fetchall()
        if not rows:
            print("No rows found in macrostrat.intervals.")
        else:
            print("Rows found in macrostrat.intervals:", rows)


if __name__ == "__main__":
    asyncio.run(insert_rockd())