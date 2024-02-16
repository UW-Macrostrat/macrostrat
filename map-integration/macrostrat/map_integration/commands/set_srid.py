from psycopg2.sql import Identifier

from ..database import db
from ..utils import MapInfo


def apply_srid(source: MapInfo, srid: int, force: bool = False):
    """Set the georeference for a map source."""
    if not force:
        print("This command will set the georeference for a map source.")
        print("This will overwrite any existing georeference.")
        print("Are you sure you want to continue? [y/N]")
        if input().lower() != "y":
            return

    geom_type_index = {
        "points": "Point",
        "linework": "MultiLineString",
        "polygons": "MultiPolygon",
    }

    for ftype in ["points", "linework", "polygons"]:
        table = Identifier("sources", f"{source.slug}_{ftype}")
        print(f"Setting georeference for {source.slug} to {srid}")
        sql = "UPDATE {table} SET geom = ST_Transform(geom, :srid)"
        if force:
            sql = "ALTER TABLE {table} ALTER COLUMN geom TYPE geometry(:ftype, :srid) USING ST_SetSRID(geom, :srid)"
        db.run_sql(
            sql,
            {
                "srid": srid,
                "source_id": source.id,
                "table": table,
                "ftype": geom_type_index[ftype],
            },
        )
