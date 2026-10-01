from psycopg2.sql import Identifier
from rich import print

from macrostrat.database import Database

from ..database import sql_file
from ..utils import MapInfo


def make_lookup(db: Database, source: MapInfo):
    """Rebuild a map source's rows in `maps.lookup` and refresh its stats.

    Each polygon gets its unit, strat-name and lith matches, its best age and a
    colour for tiles.
    """
    refresh_lookup_table(db, source.id)
    update_source_stats(db, source.id)


def refresh_lookup_table(db: Database, source_id: int):
    """Rebuild this source's rows in `maps.lookup`.

    The delete and the insert share a transaction, so the source is never seen
    with no lookup rows: `run_sql` otherwise commits each statement on its own.
    """
    with db.transaction():
        db.run_sql(sql_file("build-lookup-table"), {"source_id": source_id})


def update_source_stats(db: Database, source_id: int):
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
