from os import environ
from macrostrat.database import Database
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import text

INTEGRATION_DATABASE_URL = environ.get("INTEGRATION_DATABASE_URL", None)
MACROSTRAT_DATABASE_URL = environ.get("MACROSTRAT_DATABASE_URL", None)

db = Database(INTEGRATION_DATABASE_URL)


def database_connection():
    """Return a Psycopg2 connection to the database."""
    conn = db.engine.raw_connection()
    conn.set_client_encoding("UTF8")
    return conn


def sql_file(key: str) -> str:
    """Return the contents of a SQL file."""
    return text((Path(__file__).parent / "procedures" / (key + ".sql")).read_text())


def create_fixtures():
    raise Exception(
        "This is currently not representative of the Macrostrat v2 database design."
    )
    sql_files = list(Path(__file__).parent.glob("fixtures/*.sql"))
    sql_files.sort()
    for f in sql_files:
        db.exec_sql(f)
