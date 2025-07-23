import os

import pymysql
import requests
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Get DB credentials from environment
host = os.getenv("MARIADB_HOST")
user = os.getenv("MARIADB_USER")
password = os.getenv("MARIADB_PASSWORD")
database = os.getenv("MARIADB_DATABASE")

# Connect to MariaDB using env vars
conn = pymysql.connect(
    host=host,
    user=user,
    password=password,
    database=database,
)


API_URL = "http://localhost:5500/usage-stats"

BATCH_SIZE = 1000
last_id = 0

with conn:
    with conn.cursor() as cursor:
        while True:
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
                break

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

            data = {
                "data": payload,
            }

            try:
                response = requests.post(API_URL, json=data)
                response.raise_for_status()
                print(
                    f"Sent batch starting with idvisit {rows[0][0]}, count: {len(rows)}"
                )
            except requests.exceptions.RequestException as e:
                print(e)
                break

            last_id = rows[-1][0]
