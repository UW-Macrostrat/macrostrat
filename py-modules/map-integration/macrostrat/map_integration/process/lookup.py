from psycopg2.sql import Identifier
from rich import print

from macrostrat.core.exc import MacrostratError

from ..database import get_database, sql_file
from ..utils import MapInfo


def make_lookup(source: MapInfo):
    """
    Inserts/updates a given map source's records in public.lookup_<scale>
    Computes things like best_age_top/bottom and the appropriate color for each polygon
    """
    db = get_database()
    row = db.run_query(
        "SELECT scale FROM maps.sources WHERE source_id = :source_id",
        {"source_id": source.id},
    ).first()

    # Raised rather than `sys.exit(1)`, which the version-1 command used: these
    # steps now run over a selector, and killing the process on the first map
    # without a scale would abandon the other 113.
    if row is None:
        raise MacrostratError(f"Source {source.id} was not found in maps.sources")
    if row.scale is None:
        raise MacrostratError(f"Source {source.id} is missing a scale")

    refresh_lookup_table(db, source.id, row.scale)
    update_source_stats(db, source.id)


def refresh_lookup_table(db, source_id: int, scale: str):
    """Rebuild this source's rows in `lookup_<scale>`."""
    params = {
        # `scale` names two tables, not one: the scale-partitioned view of
        # `maps` and the lookup table beside it.
        "lookup_table": Identifier(f"lookup_{scale}"),
        "scale_table": Identifier("maps", scale),
        "source_id": source_id,
    }

    db.run_sql(
        """
        DELETE FROM {lookup_table}
        WHERE map_id IN (
            SELECT map_id FROM {scale_table} WHERE source_id = :source_id
        )
        """,
        params,
    )
    db.run_sql(sql_file("build-lookup-table"), params)


def update_source_stats(db, source_id: int):
    """Record the source's area and feature count from its staging table."""
    primary_table = db.run_query(
        "SELECT primary_table FROM maps.sources WHERE source_id = :source_id",
        {"source_id": source_id},
    ).scalar()

    if primary_table is None:
        # A map ingested through a shared staging table leaves `primary_table`
        # null -- it is `UNIQUE`, and it names *the table this map came through*,
        # which 114 members of one arrival cannot each claim. There is no single
        # table to measure, so the stats are skipped rather than the step failing
        # on `sources."None"`.
        print(
            f"[dim]No primary table for source {source_id}; skipping area and"
            " feature counts."
        )
        return

    db.run_sql(
        """
        WITH second AS (
          SELECT ST_MakeValid(geom) geom FROM {primary_table}
        ),
        third AS (
          SELECT round(sum(ST_Area(geom::geography)*0.000001)) area, COUNT(*) features
          FROM second
        )
        UPDATE maps.sources AS a
        SET area = s.area, features = s.features
        FROM third AS s
        WHERE a.source_id = :source_id;

        UPDATE maps.sources
        SET display_scales = ARRAY[scale]
        WHERE source_id = :source_id;
        """,
        {
            "primary_table": Identifier("sources", primary_table),
            "source_id": source_id,
        },
    )
