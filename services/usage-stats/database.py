from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)

async def connect_engine():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT * FROM macrostrat.intervals LIMIT 1"))
        rows = await result.fetchall()  # <-- await here
        if not rows:
            print("No rows found in macrostrat.intervals.")
        else:
            print("Rows found in macrostrat.intervals:", rows)

if __name__ == "__main__":
    asyncio.run(connect_engine())
