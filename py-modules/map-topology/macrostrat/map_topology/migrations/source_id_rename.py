"""Rename map-source foreign keys in `map_bounds` to `source_id`."""

from psycopg.sql import Identifier

from macrostrat.database import Database
from macrostrat.schema_management import Migration, _any, _not, has_columns

#: (schema, table, old column name)
RENAMED = [
    ("map_bounds", "map_area", "id"),
    ("map_bounds", "map_topo", "map_id"),
    ("map_bounds", "map_priority", "map_id"),
]


class SourceIDRenameMigration(Migration):
    """Rename `id` / `map_id` to `source_id` in the `map_bounds` schema.

    Each of these columns is a foreign key to `maps.sources(source_id)`. The old
    names obscured that, and `map_id` collided with `maps.polygons.map_id`, which
    identifies a *polygon* and is frozen for the legacy API.

    Renames are metadata-only in Postgres: no table rewrite, no data change, and
    constraints, indexes and foreign keys follow their column automatically.

    Not renamed here: the topology identity column on
    `map_bounds_topology.map_face` and `face_identity`. It keeps the name
    `map_id`, because the topology-manager submodule already defines
    `map_face.source_id` as a self-reference -- which face a composite face was
    derived from -- so the name is taken in that schema and means something else.
    """

    name = "map-bounds-source-id"
    subsystem = "maps"
    description = "Rename map_bounds source keys to source_id"
    readiness_state = "ga"

    # A column rename carries every value with it: schema change only.
    destructive = False

    # Any outstanding old name is enough to run: `apply` renames column by
    # column, so a partially-renamed database is finished off rather than
    # blocked. This also covers a database renamed by hand.
    preconditions = [
        _any(has_columns(schema, table, old) for schema, table, old in RENAMED)
    ]

    # Both halves matter. A fresh build from the declarative fixtures satisfies
    # these too, which is correct: the migration is then a no-op and reads as
    # already applied rather than being attempted.
    postconditions = [
        *[has_columns(schema, table, "source_id") for schema, table, _ in RENAMED],
        *[_not(has_columns(schema, table, old)) for schema, table, old in RENAMED],
    ]

    def apply(self, database: Database):
        for schema, table, old in RENAMED:
            if not _column_exists(database, schema, table, old):
                # Already renamed, by an earlier run or by hand.
                continue
            database.run_sql(
                "ALTER TABLE {table} RENAME COLUMN {old_column} TO source_id",
                dict(table=Identifier(schema, table), old_column=Identifier(old)),
                raise_errors=True,
            )


def _column_exists(db: Database, schema: str, table: str, column: str) -> bool:
    """Check `information_schema` directly rather than the reflection cache.

    `db.inspector` memoizes per table, so a check made after an earlier rename in
    the same run can return stale columns.
    """
    return (
        db.run_query(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.columns
              WHERE table_schema = :schema
                AND table_name = :table
                AND column_name = :column
            )
            """,
            dict(schema=schema, table=table, column=column),
        ).scalar()
        is True
    )
