from psycopg2.sql import Identifier

from ..database import db


def get_match_count(source_id: int, table: Identifier):
    return db.run_query(
        """
        SELECT count(*) FROM {table} sn
        JOIN maps.polygons p ON p.map_id = sn.map_id
        WHERE p.source_id = :source_id;
        """,
        {"source_id": source_id, "table": table},
    ).scalar()
