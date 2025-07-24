import os
import pymysql
import requests
from dotenv import load_dotenv
import asyncio

from database import insert

# Load variables from .env file
load_dotenv()

# Get DB credentials from environment
host = os.getenv("MARIADB_HOST")
user = os.getenv("MARIADB_USER")
password = os.getenv("MARIADB_PASSWORD")
database = os.getenv("MARIADB_DATABASE")

# Connect to MariaDB using env vars
matomo_conn = pymysql.connect(
    host=host,
    user=user,
    password=password,
    database=database,
)

BATCH_SIZE = 1000
payload = []

with matomo_conn:
    with matomo_conn.cursor() as cursor:
        # Keyset-based pagination using idvisit
        cursor.execute(
            """
            SELECT
                location_latitude AS lat,
                location_longitude AS lng,
                visit_first_action_time AS date,
                idvisitor AS ip
            FROM matomo_log_visit a
            WHERE 
                location_latitude IS NOT NULL
                AND location_longitude IS NOT NULL
                AND visit_first_action_time > '2025-07-02'
            LIMIT %s
        """,
            (BATCH_SIZE),
        )

        rows = cursor.fetchall()

        if not rows:
            print("No more rows to process.")
        else:
            payload = [
                {
                    "lat": float(row[0]),
                    "lng": float(row[1]),
                    "date": row[2].isoformat(),
                    "ip": row[3],
                }
                for row in rows
            ]
            asyncio.run(insert(payload, "macrostrat"))