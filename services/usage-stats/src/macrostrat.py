import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.insert import insert
from src.last_id import get_last_id

async def get_data(last_id, mariadb_url, db_url):
    BATCH_SIZE = 1000  # Adjust as needed

    raw_url = mariadb_url

    # Ensure the URL uses asyncmy driver
    if raw_url.startswith("mysql://"):
        raw_url = raw_url.replace("mysql://", "mysql+asyncmy://", 1)
    else:
        raise ValueError(
            "Invalid DATABASE_URL: must start with mysql:// or mysql+asyncmy://"
        )

    DATABASE_URL = raw_url

    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=True)

    # Async session factory
    AsyncSessionLocal = sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession
    )

    async with AsyncSessionLocal() as session:
        query = text(
            """
            SELECT
                location_latitude AS lat,
                location_longitude AS lng,
                visit_first_action_time AS date,
                idvisitor AS ip,
                idvisit as matomo_id
            FROM matomo_log_visit
            WHERE 
                idvisit > :last_id
                AND location_latitude IS NOT NULL
                AND location_longitude IS NOT NULL
                AND visit_first_action_time > '2025-07-02'
            LIMIT :batch_size
        """
        )

        result = await session.execute(
            query, {"last_id": last_id, "batch_size": BATCH_SIZE}
        )
        rows = result.fetchall()

        if not rows:
            print("No more rows to process.")
            return

        payload = [
            {
                "lat": float(row.lat),
                "lng": float(row.lng),
                "date": row.date,
                "ip": str(row.ip),
                "matomo_id": row.matomo_id,
            }
            for row in rows
        ]

        await insert(payload, "macrostrat", db_url)


async def get_macrostrat_data(mariadb_url, db_url):
    last_id = await get_last_id("macrostrat", db_url)
    await get_data(last_id, mariadb_url, db_url)
    print("Data fetching completed.")
