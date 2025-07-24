import os
import pymysql
import requests
from dotenv import load_dotenv
import asyncio

from database import insert_rockd

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
last_id = 0
payload = []

with matomo_conn:
    with matomo_conn.cursor() as cursor:
        # Keyset-based pagination using idvisit
        cursor.execute(
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

        rows = cursor.fetchall()

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
                    "date": str(row[2]),
                    "ip": str(row[3]),
                }
                for row in rows
            ]

            asyncio.run(insert_rockd(payload))