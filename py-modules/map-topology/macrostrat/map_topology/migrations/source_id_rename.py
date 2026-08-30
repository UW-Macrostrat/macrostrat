"""Name `maps.sources` keys `source_id` across the `map_bounds` schema."""

from psycopg.sql import Identifier

from macrostrat.database import Database
from macrostrat.schema_management import Migration, _any, _not, has_columns

RENAMED = [("map_topo", "map_id"), ("map_priority", "map_id")]


class SourceIDRenameMigration(Migration):
    """Rename `map_bounds` foreign keys to `maps.sources` as `source_id`.

    `map_area` keeps `id`: the topology-manager submodule hard-codes that name
    for the boundary table, in `__edge_relation`'s foreign key and in `l.id`
    throughout its procedures. It gets a generated alias instead -- readable, but
    not writable, so inserts still target `id`.
    """

    name = "map-bounds-source-id"
    subsystem = "maps"
    description = "Name maps.sources keys `source_id` across map_bounds"
    readiness_state = "ga"
    destructive = False

    preconditions = [
        _any(
            [
                *[has_columns("map_bounds", t, old) for t, old in RENAMED],
                _not(has_columns("map_bounds", "map_area", "source_id")),
            ]
        )
    ]

    postconditions = [
        *[has_columns("map_bounds", t, "source_id") for t, _ in RENAMED],
        *[_not(has_columns("map_bounds", t, old)) for t, old in RENAMED],
        has_columns("map_bounds", "map_area", "source_id"),
    ]

    def apply(self, database: Database):
        for table, old in RENAMED:
            if _has_column(database, table, old):
                database.run_sql(
                    "ALTER TABLE map_bounds.{table}"
                    " RENAME COLUMN {old_column} TO source_id",
                    dict(table=Identifier(table), old_column=Identifier(old)),
                    raise_errors=True,
                )
        if not _has_column(database, "map_area", "source_id"):
            database.run_sql(
                "ALTER TABLE map_bounds.map_area ADD COLUMN source_id integer"
                " GENERATED ALWAYS AS (id) STORED UNIQUE",
                raise_errors=True,
            )


def _has_column(db: Database, table: str, column: str) -> bool:
    """Query `information_schema`; `db.inspector` caches per table and goes stale."""
    return (
        db.run_query(
            "SELECT true FROM information_schema.columns"
            " WHERE table_schema = 'map_bounds'"
            "   AND table_name = :table AND column_name = :column",
            dict(table=table, column=column),
        ).scalar()
        is True
    )
