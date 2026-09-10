from pathlib import Path

from macrostrat.core.database import get_database


def database_connection():
    """Return a DBAPI connection to the database."""
    db = get_database()
    conn = db.engine.raw_connection()
    # psycopg3 dropped `set_client_encoding`; the encoding is an ordinary GUC.
    with conn.cursor() as cursor:
        cursor.execute("SET client_encoding TO 'UTF8'")
    return conn


def sql_file(key: str) -> str:
    """Return the contents of a sql file."""
    return (Path(__file__).parent / "procedures" / (key + ".sql")).read_text()
