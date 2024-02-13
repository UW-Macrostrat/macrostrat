import time
from pathlib import Path

from psycopg2.sql import SQL, Identifier
from sqlalchemy.sql import text

from ..database import db, sql_file
from ..utils import MapInfo


def create_rgeom(source: MapInfo, use_maps_schema: bool = False):
    """Create a unioned reference geometry for a map source"""
    start = time.time()
    source_id = source.id

    q = "SELECT primary_table FROM maps.sources WHERE source_id = :source_id"
    row = db.run_query(q, {"source_id": source_id}).first()

    name = row.primary_table

    if use_maps_schema:
        table = Identifier("maps", "polygons")
        where = "source_id = :source_id"
    else:
        table = Identifier("sources", name)
        where = "not coalesce(omit, false)"

        print("Validating geometry...")
        q = "UPDATE {primary_table} SET geom = ST_Buffer(geom, 0)"
        db.run_query(q, {"primary_table": table})

    print("Creating reference geometry...")
    db.run_query(
        sql_file("set-rgeom"),
        dict(source_id=source_id, primary_table=table, where_clause=SQL(where)),
    )

    end = time.time()

    print(f"Done in {end - start} s")


def create_webgeom(source_id: int):
    """Create a geometry for use on the web"""
    sql = sql_file("set-webgeom")
    db.run_sql(sql, {"source_id": source_id})
