from os import environ
from macrostrat.database import Database
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

MACROSTRAT_DATABASE_URL = environ.get("MACROSTRAT_DATABASE_URL", None)

db = Database(MACROSTRAT_DATABASE_URL)


def database_connection():
    """Return a Psycopg2 connection to the database."""
    conn = db.engine.raw_connection()
    conn.set_client_encoding("UTF8")
    return conn


def sql_file(key: str) -> str:
    """Return the contents of a SQL file."""
    return (Path(__file__).parent / "procedures" / (key + ".sql")).read_text()
