from psycopg2.sql import Identifier, Literal

from macrostrat.utils import get_logger

from ..database import get_database, sql_file
from ..utils import MapInfo, feature_counts

log = get_logger(__name__)


def copy_to_maps(source: MapInfo, delete_existing: bool = False, scale: str = None):
    """
    Copy a single map's data to the maps schema
    """
    db = get_database()

    info = source
    source_id = info.id
    slug = info.slug

    data = feature_counts(db, info)

    log.info(
        "Source %s has %s polygons, %s lines, %s points already in database",
        slug,
        *data,
    )

    has_any_features = data.n_polygons > 0 or data.n_lines > 0 or data.n_points > 0

    if not delete_existing and has_any_features:
        raise ValueError(
            f"Source {source_id} already has data in the maps schema. Aborting."
        )

    if scale is None:
        scale = db.run_query(
            "SELECT scale FROM maps.sources WHERE source_id = :source_id",
            dict(source_id=source_id),
        ).scalar()

    if scale is None:
        raise ValueError(
            "No scale provided and no scale found in the sources table. Aborting."
        )

    if has_any_features:
        _delete_map_data(source_id)

    db.run_sql(
        sql_file("copy-to-maps-schema"),
        dict(
            source_id=Literal(source_id),
            polygons_table=Identifier("sources", slug + "_polygons"),
            lines_table=Identifier("sources", slug + "_lines"),
            points_table=Identifier("sources", slug + "_points"),
            scale=Literal(scale),
        ),
    )


def _delete_map_data(source_id):
    db = get_database()
    db.run_sql(
        """DELETE FROM maps.polygons WHERE source_id = :source_id;
        DELETE FROM maps.lines WHERE source_id = :source_id;
        DELETE FROM maps.points WHERE source_id = :source_id;""",
        dict(source_id=source_id),
    )
