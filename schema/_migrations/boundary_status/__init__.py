from macrostrat.database import Database
from macrostrat.schema_management import Migration

# Columns the SQL retypes to the `macrostrat` enum named like the column
_UNCONVERTED = """
SELECT count(*) FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'macrostrat'
  AND c.relkind = 'r'
  AND c.relname IN (
    'interval_boundaries', 'interval_boundaries_scratch', 'unit_boundaries',
    'unit_boundaries_backup', 'unit_boundaries_scratch', 'unit_boundaries_scratch_old'
  )
  AND a.attname IN ('boundary_status', 'boundary_type')
  AND NOT a.attisdropped
  AND a.atttypid IS DISTINCT FROM to_regtype('macrostrat.' || a.attname)
"""


def _unconverted_columns(db: Database) -> bool:
    """A boundary column still has a per-table or `public` enum type."""
    return db.run_query(_UNCONVERTED).scalar() > 0


class BoundaryStatusMigration(Migration):
    name = "boundary-status"
    description = """
    Relocate custom types for Macrostrat schema
    """
    readiness_state = "ga"

    # Keyed on the columns, not the types: the declarative schema creates the
    # `macrostrat` types too, which would read as applied with nothing retyped.
    preconditions = [_unconverted_columns]
    postconditions = [lambda db: not _unconverted_columns(db)]
