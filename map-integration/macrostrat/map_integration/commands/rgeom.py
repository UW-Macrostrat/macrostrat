from ..database import db, sql_file
from pathlib import Path
from psycopg2.extensions import AsIs
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.sql import text
import time


def create_rgeom(source_id: int):
    """Create a unioned reference geometry for a map source"""
    start = time.time()

    q = "SELECT slug FROM maps.sources WHERE source_id = %(source_id)s"
    key = db.session.execute(text(q), dict(source_id=source_id)).scalar()

    print("Validating geometry...")
    cursor = db.engine.connect()
    q = "UPDATE sources.%(primary_table)s SET geom = ST_Buffer(geom, 0)"
    table = None
    for name in [key, f"{key}_polygons"]:
        try:
            table = AsIs(name)
            cursor.execute(q, {"primary_table": table})
        except ProgrammingError:
            pass

    print("Creating reference geometry...")
    sqlfile = Path(__file__).parent.parent / "procedures" / "set-rgeom.sql"
    cursor.execute(sqlfile.read_text(), dict(source_id=source_id, primary_table=table))

    end = time.time()

    print(f"Done in {end - start} s")


def create_webgeom(source_id: int):
    """Create a geometry for use on the web"""

    sql = sql_file("set-webgeom")
    # Get the primary table of the target source
    db.session.execute(text(sql), params=dict(source_id=source_id))
