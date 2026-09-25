"""Name `map_priority`'s columns for what they hold: the resolved map and its member."""

from psycopg.sql import Identifier

from macrostrat.database import Database
from macrostrat.schema_management import Migration, _any, _not, has_columns

RENAMED = [("source_id", "map_id"), ("via", "member_id")]


class MapPriorityColumnsMigration(Migration):
    """`map_priority(map_layer, source_id, priority_path, via)` becomes
    `(map_layer, map_id, priority_path, member_id)`.

    One row per registered compilation per *resolved map*, so the map column is
    `map_id`, as it is on `map_face`; `member_id` is the member of the compilation
    the resolved map belongs to, which `via` named after the route rather than the
    thing. The table is derived and is rebuilt by `sync-priority-paths`, so the
    rename carries no data that could not be regenerated.
    """

    name = "map-priority-columns"
    subsystem = "maps"
    description = "map_priority: source_id -> map_id, via -> member_id"
    readiness_state = "ga"
    destructive = False

    preconditions = [
        _any([has_columns("map_bounds", "map_priority", old) for old, _ in RENAMED])
    ]
    postconditions = [
        *[has_columns("map_bounds", "map_priority", new) for _, new in RENAMED],
        *[_not(has_columns("map_bounds", "map_priority", old)) for old, _ in RENAMED],
    ]

    def apply(self, database: Database):
        for old, new in RENAMED:
            if _has_column(database, old):
                database.run_sql(
                    "ALTER TABLE map_bounds.map_priority RENAME COLUMN {old} TO {new}",
                    dict(old=Identifier(old), new=Identifier(new)),
                    raise_errors=True,
                )


def _has_column(db: Database, column: str) -> bool:
    return (
        db.run_query(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.columns
              WHERE table_schema = 'map_bounds'
                AND table_name = 'map_priority'
                AND column_name = :column
            )
            """,
            dict(column=column),
        ).scalar()
        is True
    )
