from psycopg2.sql import Identifier, Literal
from rich import print

from macrostrat.core.exc import MacrostratError
from macrostrat.map_utils.slugs import STAGING_KINDS, table_prefix
from macrostrat.utils import get_logger

from ..database import get_database, sql_file
from ..utils import MapInfo, feature_counts, table_exists

log = get_logger(__name__)

# Columns an ingest is expected to have made an attempt at. Individual nulls are
# ordinary -- plenty of map units have no stratigraphic name, and a water polygon
# has no lithology -- but a column that is null on *every* row of a source means
# the step that fills it never ran. Both of ours are cheap to leave out and
# expensive to notice later: the map inserts, renders, and looks finished, and
# the absence only shows up as a unit that will not colour or match a unit.
ATTEMPTED_COLUMNS = ("lith", "t_interval", "b_interval")


def copy_to_maps(
    db,
    source: MapInfo,
    *,
    delete_existing: bool = False,
    scale: str = None,
    staging_prefix: str = None,
    allow_unattributed: bool = False,
):
    """Copy a single map's data from the `sources` schema to the `maps` schema.

    `staging_prefix` names the `sources.<prefix>_{polygons,lines,points}` triple
    and defaults to the map's slug, which is the ordinary case: one ingestion,
    one set of staging tables named after it.

    A **compilation whose members share one staging table** passes the shared
    prefix instead -- NGS's 114 members all stage into `sources.ngs_*`, and
    `maps.sources.primary_table` cannot name it for them because that column is
    `UNIQUE`. Nothing else has to change: the copy filters on `source_id`, so a
    shared table is just a wider table.

    Polygons are required; a map without a lines or points table simply has none.
    Refuses a source whose `lith`, `t_interval` or `b_interval` is null on every
    polygon -- see `ATTEMPTED_COLUMNS`. `allow_unattributed` is the way past it,
    for a map that genuinely has none of the attribute in question.
    """
    source_id = source.id
    prefix = staging_prefix or table_prefix(source.slug)

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

    kinds = [
        kind
        for kind in STAGING_KINDS
        if table_exists(db, f"{prefix}_{kind}", schema="sources")
    ]
    if "polygons" not in kinds:
        raise MacrostratError(
            f"Refusing to insert: sources.{prefix}_polygons does not exist"
        )
    # Checked before existing data is cleared, so a refusal leaves the map as it was
    _check_attempted_columns(db, prefix, source_id, allow_unattributed)

    if has_any_features:
        _delete_map_data(db, source_id)

    params = dict(
        source_id=Literal(source_id),
        polygons_table=Identifier("sources", prefix + "_polygons"),
        lines_table=Identifier("sources", prefix + "_lines"),
        points_table=Identifier("sources", prefix + "_points"),
        polygons_table_maps=Identifier("maps", "polygons_" + scale),
        lines_table_maps=Identifier("maps", "lines_" + scale),
        scale=Literal(scale),
    )
    # Polygons first: a rejected polygon insert must abort before lines go in
    for kind in kinds:
        db.run_sql(sql_file(f"copy-{kind}-to-maps"), params, raise_errors=True)


def remove(db, source: MapInfo):
    """Remove a map's data from the `maps` schema.

    This is the inverse of `copy_to_maps`, and is used when a map is being
    re-ingested or removed. It does not delete the source record itself, only
    the geometry and attribute data in the `maps` schema.
    """
    data = feature_counts(db, source)

    log.info(
        "Deleting source %s with %s polygons, %s lines, %s points from database",
        source.slug,
        *data,
    )

    if data.n_polygons == 0 and data.n_lines == 0 and data.n_points == 0:
        log.warning(
            "Source %s has no data in the maps schema. Nothing to delete.", source.slug
        )
        return

    _delete_map_data(db, source.id)


def _delete_map_data(db, source_id):
    db.run_sql(
        """DELETE FROM maps.polygons WHERE source_id = :source_id;
        DELETE FROM maps.lines WHERE source_id = :source_id;
        DELETE FROM maps.points WHERE source_id = :source_id;""",
        dict(source_id=source_id),
    )


def _check_attempted_columns(db, prefix: str, source_id: int, allow: bool):
    """Refuse a source that has had no attribute crosswalk applied to it.

    Counted on the staging table rather than `maps.polygons`, so the check reads
    the thing the ingest is responsible for, and reported per column so the
    message says which step to go and run.

    Also refuses a source with no polygons to insert.
    """
    counts = db.run_query(
        """
        SELECT count(*) AS n_rows,
               count(lith) AS lith,
               count(t_interval) AS t_interval,
               count(b_interval) AS b_interval
        FROM {polygons_table}
        WHERE source_id = :source_id AND NOT coalesce(omit, false)
        """,
        dict(
            polygons_table=Identifier("sources", prefix + "_polygons"),
            source_id=source_id,
        ),
    ).one()

    if counts.n_rows == 0:
        raise MacrostratError(
            f"Refusing to insert: sources.{prefix}_polygons has no polygons"
            f" for source {source_id}"
        )

    empty = [c for c in ATTEMPTED_COLUMNS if getattr(counts, c) == 0]
    if not empty:
        return

    detail = (
        f"{', '.join(empty)} "
        f"{'is' if len(empty) == 1 else 'are'} null on all "
        f"{counts.n_rows} polygons of {prefix} source {source_id}"
    )

    if allow:
        # Loud, and on stdout rather than in the log, because the whole point is
        # that this is otherwise invisible in a 114-map sweep.
        print(f"[yellow bold]warning[/] {detail} [dim](--allow-unattributed)[/]")
        return

    raise MacrostratError(
        f"Refusing to insert: {detail}.",
        details=(
            "These come from the attribute crosswalk, not the geometry load, so"
            " an entirely null column means that step has not run. Apply it, or"
            " pass --allow-unattributed if this map genuinely has none."
        ),
    )
