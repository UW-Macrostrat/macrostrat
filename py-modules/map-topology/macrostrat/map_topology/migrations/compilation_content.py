"""Record where a compilation's polygons came from."""

from macrostrat.database import Database
from macrostrat.schema_management import Migration

_COLUMN_EXISTS = """
SELECT EXISTS (
  SELECT 1 FROM information_schema.columns
  WHERE table_schema = 'map_bounds'
    AND table_name = 'compilation'
    AND column_name = 'content'
)
"""

# The backfill, not the column, is what only this migration produces. Keying the
# postcondition on the column alone marks it applied when the declarative chunk
# adds the column first -- which is exactly what happened, leaving `bc-surface`
# and `mid-atlantic-surface` holding polygons with no recorded provenance.
_UNRECORDED = """
SELECT EXISTS (
  SELECT 1 FROM map_bounds.compilation c
  WHERE map_bounds.holds_polygons(c.source_id) AND c.content IS NULL
)
"""


class CompilationContent(Migration):
    """Add `map_bounds.compilation.content`.

    NULL for a virtual compilation, `derived` for one materialized from its
    members, `ingested` for one whose polygons arrived with it. Existing rows are
    backfilled: a compilation holding polygons today got them from `materialize`,
    so it is `derived`; the rest stay NULL.

    The column is a safety interlock as much as a description. Only `derived`
    content can be put back where it came from -- without the distinction,
    `dematerialize` would happily delete SGMC's 312,286 ingested polygons, having
    taken them for a cache.
    """

    name = "map-bounds-compilation-content"
    subsystem = "maps"
    description = "Record where a compilation's polygons came from"
    readiness_state = "ga"
    destructive = False

    preconditions = [
        lambda db: not _scalar(db, _COLUMN_EXISTS) or _scalar(db, _UNRECORDED)
    ]
    postconditions = [
        lambda db: _scalar(db, _COLUMN_EXISTS),
        lambda db: not _scalar(db, _UNRECORDED),
    ]

    def apply(self, database: Database):
        database.run_sql(
            """
            ALTER TABLE map_bounds.compilation
              ADD COLUMN IF NOT EXISTS content text
                CHECK (content IN ('ingested', 'derived'))
            """
        )
        # Anything already holding polygons was materialized from its members --
        # `materialize` is the only thing that has ever written them.
        database.run_sql(
            """
            UPDATE map_bounds.compilation c
            SET content = 'derived'
            WHERE map_bounds.holds_polygons(c.source_id)
              AND c.content IS NULL
            """
        )


def _scalar(db: Database, sql: str) -> bool:
    return db.run_query(sql).scalar() is True
