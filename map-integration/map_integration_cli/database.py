from os import environ
from macrostrat.database import Database
from dotenv import load_dotenv

load_dotenv()

MACROSTRAT_DATABASE_URL = environ.get("MACROSTRAT_DATABASE_URL", None)

db = Database(MACROSTRAT_DATABASE_URL)


def database_connection():
    """Return a PsycoPG2 connection to the database."""
    return db.engine.raw_connection()
