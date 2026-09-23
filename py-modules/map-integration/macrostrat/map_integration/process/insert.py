from psycopg2.sql import Identifier, Literal
from rich import print

from macrostrat.core.exc import MacrostratError
from macrostrat.utils import get_logger

from ..database import get_database, sql_file
from ..utils import MapInfo, feature_counts

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
    `UNIQUE`. Nothing else has to change: `copy-to-maps-schema.sql` already
    filters on `source_id`, so a shared table is just a wider table.

    Refuses a source whose `lith`, `t_interval` or `b_interval` is null on every
    polygon -- see `ATTEMPTED_COLUMNS`. `allow_unattributed` is the way past it,
    for a map that genuinely has none of the attribute in question.
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

    _check_attempted_columns(db, prefix, source_id, allow_unattributed)

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


def run_insert(
    source: MapInfo,
    *,
    delete_existing: bool = False,
    scale: str = None,
    staging_prefix: str = None,
    allow_unattributed: bool = False,
):
    """Copy one map's data to the maps schema, resolving the database itself."""
    copy_to_maps(
        get_database(),
        source,
        delete_existing=delete_existing,
        scale=scale,
        staging_prefix=staging_prefix,
        allow_unattributed=allow_unattributed,
    )


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

    A source with no polygons at all is not this check's business -- a
    lines-and-points map is legitimate, and `feature_counts` has already spoken.
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
        return

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
