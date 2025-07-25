import asyncio
import os
from datetime import datetime

import asyncmy
from dotenv import load_dotenv
from src.insert import insert
from src.last_id import get_last_id

BATCH_SIZE = 1000  # Adjust batch size as needed


async def get_data(last_id):
    load_dotenv()

    host = os.getenv("MARIADB_HOST")
    user = os.getenv("MARIADB_USER")
    password = os.getenv("MARIADB_PASSWORD")
    database = os.getenv("MARIADB_DATABASE")

    matomo_conn = await asyncmy.connect(
        host=host,
        user=user,
        password=password,
        database=database,
    )

    try:
        async with matomo_conn.cursor() as cursor:
            await cursor.execute(
                """
                SELECT
                    location_latitude AS lat,
                    location_longitude AS lng,
                    visit_first_action_time AS date,
                    idvisitor AS ip,
                    idvisit as matomo_id
                FROM matomo_log_visit
                WHERE 
                    idvisit > %s
                    AND location_latitude IS NOT NULL
                    AND location_longitude IS NOT NULL
                    AND visit_first_action_time > '2025-07-02'
                LIMIT %s
                """,
                (last_id, BATCH_SIZE),
            )

            rows = await cursor.fetchall()

            if not rows:
                print("No more rows to process.")
                return

            payload = []

            for row in rows:
                parsed = {
                    "lat": float(row[0]),
                    "lng": float(row[1]),
                    "date": row[2],
                    "ip": str(row[3]),
                    "matomo_id": row[4],
                }
                payload.append(parsed)

            await insert(payload, "macrostrat")

    finally:
        await matomo_conn.ensure_closed()


async def fetch_last_id():
    return await get_last_id("macrostrat")


async def fetch_matomo_data(last_id):
    await get_data(last_id)


async def get_macrostrat_data():
    last_id = await fetch_last_id()
    await fetch_matomo_data(last_id)
    print("Data fetching completed.")


if __name__ == "__main__":
    asyncio.run(get_macrostrat_data())
