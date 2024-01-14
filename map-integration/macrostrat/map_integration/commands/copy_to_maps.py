from typing import Union

from macrostrat.utils import get_logger
from psycopg2.sql import Identifier, Literal

from ..database import db, sql_file
from ..utils import MapInfo, get_map_info

log = get_logger(__name__)


def copy_to_maps(source: str, delete_existing: bool = False, scale: str = None):
    """
    Copy a single map's data to the maps schema
    """

    info: MapInfo = get_map_info(db, source)
    source_id = info.id
    slug = info.slug

    res = db.run_query(
        """SELECT 
        (SELECT count(*) FROM maps.polygons WHERE source_id = :source_id) AS polygon_count,
        (SELECT count(*) FROM maps.lines WHERE source_id = :source_id) AS line_count,
        (SELECT count(*) FROM maps.points WHERE source_id = :source_id) AS point_count;""",
        dict(source_id=source_id),
    )

    data = res.first()

    log.info(
        "Source %s has %s polygons, %s lines, %s points already in database",
        slug,
        *data,
    )

    has_any_features = (
        data.polygon_count > 0 or data.line_count > 0 or data.point_count > 0
    )

    if not delete_existing and has_any_features:
        raise ValueError(
            f"Source {source_id} already has data in the maps schema. Aborting."
        )

    if has_any_features:
        db.run_sql(
            """DELETE FROM maps.polygons WHERE source_id = :source_id;
            DELETE FROM maps.lines WHERE source_id = :source_id;
            DELETE FROM maps.points WHERE source_id = :source_id;""",
            dict(source_id=source_id),
        )

    queryfile = sql_file("copy-to-maps-schema")
    db.run_sql(
        queryfile,
        dict(
            source_id=Literal(source_id),
            polygons_table=Identifier("sources", slug + "_polygons"),
            lines_table=Identifier("sources", slug + "_lines"),
            points_table=Identifier("sources", slug + "_points"),
            scale=Literal(scale),
        ),
    )
