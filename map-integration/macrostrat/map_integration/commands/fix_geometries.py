from psycopg2.sql import Identifier

from ..database import get_database
from ..utils import MapInfo


def fix_geometries(map: MapInfo):
    """Fix geometries in a map source."""
    db = get_database()
    for table in ["polygons", "lines", "points"]:
        ident = Identifier("sources", f"{map.slug}_{table}")
        db.run_sql(
            "UPDATE {table} SET geom = ST_MakeValid(geom) WHERE source_id = :source_id",
            {"source_id": map.id, "table": ident},
        )
