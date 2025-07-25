import asyncio
import os
from datetime import datetime

import asyncmy
from src.insert import insert
from src.last_id import get_last_id
from src.config import MARIADB_CONFIG

BATCH_SIZE = 1000  # Adjust batch size as needed


async def get_data(last_id):
    matomo_conn = await asyncmy.connect(
        host=MARIADB_CONFIG["host"],
        user=MARIADB_CONFIG["user"],
        password=MARIADB_CONFIG["password"],
        database=MARIADB_CONFIG["database"]
    )

    try:
        async with matomo_conn.cursor() as cursor:
            await cursor.execute(
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
            WHERE a.name LIKE %s
                AND lva.idlink_va > %s
            ORDER BY lva.idlink_va ASC
            LIMIT %s
        """,
                ("%dashboard%", last_id, BATCH_SIZE),
            )

        rows = await cursor.fetchall()

        if not rows:
            print("No more rows to process.")
        else:
            # Prepare and send batch to API
            payload = [
                {
                    "lat": float(
                        [
                            part.split("=")[1]
                            for part in str(row[1]).split("?")[1].split("&")
                            if part.startswith("lat=")
                        ][0]
                    ),
                    "lng": float(
                        [
                            part.split("=")[1]
                            for part in str(row[1]).split("?")[1].split("&")
                            if part.startswith("lng=")
                        ][0]
                    ),
                    "date": row[2],
                    "ip": str(row[3]),
                    "matomo_id": int(row[0]),
                }
                for row in rows
            ]

            await insert(payload, "rockd")

    finally:
        await matomo_conn.ensure_closed()


async def fetch_last_id():
    return await get_last_id("rockd")


async def fetch_matomo_data(last_id):
    await get_data(last_id)


async def get_rockd_data():
    last_id = await fetch_last_id()
    await fetch_matomo_data(last_id)
    print("Data fetching completed.")


if __name__ == "__main__":
    asyncio.run(get_rockd_data())
