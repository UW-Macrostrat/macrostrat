from os import environ
from fastapi import FastAPI
from macrostrat.database import Database
from pathlib import Path


# Create a FastAPI app
app = FastAPI()

# Get config from environment variables
conn_string = environ.get("DATABASE_URL")

# Set up the database
db = Database(conn_string)


def get_sql(sql_file):
    """Read an SQL file from the sql/ directory"""
    here = Path(__file__).parent
    return (here / "sql" / sql_file + ".sql").read_text()


# Cross-sections route
@app.get("/cross-section")
async def cross_section(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float
):
    """A cross-section from one geographic location to another"""

    res = db.exec_sql(get_sql("cross_section"))
    return res
