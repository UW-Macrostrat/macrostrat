from pathlib import Path

from macrostrat.database import Database
from psycopg2.extras import NamedTupleCursor

from macrostrat.core.config import PG_DATABASE

db = Database(PG_DATABASE)


def database_connection():
    """Return a Psycopg2 connection to the database."""
    conn = db.engine.raw_connection()
    conn.set_client_encoding("UTF8")
    return conn


def sql_file(key: str) -> str:
    """Return the contents of a SQL file."""
    return (Path(__file__).parent / "procedures" / (key + ".sql")).read_text()


class LegacyCommandBase:
    """Simplified base command from version 1, to provide an upgrade path."""

    def __init__(self):
        conn = db.engine.raw_connection()
        self.conn = conn
        self.cursor = conn.cursor(cursor_factory=NamedTupleCursor)
        self.pg = {
            "connection": conn,
            "cursor": self.cursor,
        }
