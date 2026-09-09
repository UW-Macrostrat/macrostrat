from typing import Annotated, Optional

from psycopg2.sql import Identifier, Literal
from typer import Option

from macrostrat.utils import get_logger

from ..database import get_database, sql_file
from ..utils import MapInfo, feature_counts

log = get_logger(__name__)


def copy_to_maps(
    db,
    source: MapInfo,
    *,
    delete_existing: bool = False,
    scale: str = None,
    staging_prefix: str = None,
):
    """Copy a single map's data from the `sources` schema to the `maps` schema.

    `staging_prefix` names the `sources.<prefix>_{polygons,lines,points}` triple
    and defaults to the map's slug, which is the ordinary case: one ingestion,
    one set of staging tables named after it.

    A **compilation whose members share one staging table** passes the shared
    prefix instead -- NGS's 114 members all stage into `sources.ngs_*`, and
    `maps.sources.primary_table` cannot name it for them because that column is
    `UNIQUE`. Nothing else has to change: `copy-to-maps-schema.sql` already
    filters on `source_id`, so a shared table is just a wider table.
    """
    source_id = source.id
    prefix = staging_prefix or source.slug

    data = feature_counts(db, source)

    log.info(
        "Source %s has %s polygons, %s lines, %s points already in database",
        source.slug,
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
        _delete_map_data(db, source_id)

    db.run_sql(
        sql_file("copy-to-maps-schema"),
        dict(
            source_id=Literal(source_id),
            polygons_table=Identifier("sources", prefix + "_polygons"),
            lines_table=Identifier("sources", prefix + "_lines"),
            points_table=Identifier("sources", prefix + "_points"),
            scale=Literal(scale),
        ),
    )


def copy_to_maps_command(
    source: MapInfo,
    delete_existing: bool = False,
    scale: str = None,
    staging_prefix: Annotated[
        Optional[str],
        Option(
            "--staging-prefix",
            help="Name the sources.<prefix>_* staging tables (default: the slug)",
        ),
    ] = None,
):
    """Copy a single map's data to the maps schema."""
    copy_to_maps(
        get_database(),
        source,
        delete_existing=delete_existing,
        scale=scale,
        staging_prefix=staging_prefix,
    )


def _delete_map_data(db, source_id):
    db.run_sql(
        """DELETE FROM maps.polygons WHERE source_id = :source_id;
        DELETE FROM maps.lines WHERE source_id = :source_id;
        DELETE FROM maps.points WHERE source_id = :source_id;""",
        dict(source_id=source_id),
    )
