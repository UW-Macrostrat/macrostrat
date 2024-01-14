import time
from pathlib import Path

from psycopg2.sql import Identifier
from sqlalchemy.sql import text

from ..database import db, sql_file


def create_rgeom(source_id: int):
    """Create a unioned reference geometry for a map source"""
    start = time.time()

    q = "SELECT slug, primary_table FROM maps.sources WHERE source_id = :source_id"
    row = db.run_query(q, {"source_id": source_id}).first()

    key = row.slug
    name = row.primary_table

    print("Validating geometry...")
    # TODO: figure out bug where we can't use $(primary_table)s here
    q = "UPDATE {primary_table} SET geom = ST_Buffer(geom, 0)"
    table = Identifier("sources", name)
    db.run_query(q, {"primary_table": table})

    print("Creating reference geometry...")
    sqlfile = Path(__file__).parent.parent / "procedures" / "set-rgeom.sql"
    db.run_query(sqlfile, dict(source_id=source_id, primary_table=table))

    end = time.time()

    print(f"Done in {end - start} s")


def create_webgeom(source_id: int):
    """Create a geometry for use on the web"""
    sql = sql_file("set-webgeom")
    db.run_query(sql, {"source_id": source_id})
