import asyncio
import os
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.insert import insert
from src.last_id import get_last_id

BATCH_SIZE = 1000  # Adjust batch size as needed

# Database URL format: mysql+asyncmy://user:password@host:port/database
DATABASE_URL = os.getenv(
    "MARIADB_URL", "mysql+asyncmy://user:password@localhost:3306/database"
)

# Create async SQLAlchemy engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_data(last_id):
    async with AsyncSessionLocal() as session:
        query = text(
            """
            SELECT
                a.Idaction AS action_id,
                a.name AS url,
                lva.server_time AS date,
                lva.idvisitor AS ip,
                lva.idlink_va
            FROM matomo_log_action a
            LEFT JOIN matomo_log_link_visit_action lva
                ON lva.idlink_va = a.Idaction
            WHERE a.name LIKE :like_pattern
                AND lva.idlink_va > :last_id
            ORDER BY lva.idlink_va ASC
            LIMIT :batch_size
            """
        )

        result = await session.execute(
            query,
            {
                "like_pattern": "%dashboard%",
                "last_id": last_id,
                "batch_size": BATCH_SIZE,
            },
        )
        rows = result.fetchall()

        if not rows:
            print("No more rows to process.")
            return

        payload = []
        for row in rows:
            url = row.url or ""
            lat = None
            lng = None
            # parse lat/lng from url query params if present
            if "?" in url:
                params_part = url.split("?", 1)[1]
                params = dict(
                    param.split("=") for param in params_part.split("&") if "=" in param
                )
                lat = float(params.get("lat", 0))
                lng = float(params.get("lng", 0))

            payload.append(
                {
                    "lat": lat,
                    "lng": lng,
                    "date": row.date,
                    "ip": str(row.ip),
                    "matomo_id": int(row.action_id),
                }
            )

        await insert(payload, "rockd")


async def fetch_last_id():
    return await get_last_id("rockd")


async def fetch_matomo_data(last_id):
    await get_data(last_id)


async def get_rockd_data():
    last_id = await fetch_last_id()
    await fetch_matomo_data(last_id)
    print("Data fetching completed.")
