"""Name compilations by how their members' extents are settled."""

from pathlib import Path

from macrostrat.database import Database
from macrostrat.schema_management import Migration

FIXTURE = Path(__file__).parents[2] / "fixtures" / "04-compilation-tables.sql"

_OLD_ROWS = """
SELECT EXISTS (
  SELECT 1 FROM map_bounds.compilation
  WHERE assembly_mode IN ('layered', 'disjoint')
)
"""

# `strpos`, not LIKE: a bare `%` in SQL run through SQLAlchemy reads as a bind.
_NEW_CONSTRAINT = """
SELECT EXISTS (
  SELECT 1 FROM pg_constraint
  WHERE conrelid = 'map_bounds.compilation'::regclass
    AND conname = 'compilation_assembly_mode_check'
    AND strpos(pg_get_constraintdef(oid), 'mosaic') > 0
)
"""

_OLD_PREDICATE = """
SELECT to_regprocedure('map_bounds.is_documentary(integer)') IS NOT NULL
"""

_CONTENT_COLUMN = """
SELECT EXISTS (
  SELECT 1 FROM information_schema.columns
  WHERE table_schema = 'map_bounds' AND table_name = 'compilation'
    AND column_name = 'content'
)
"""

_IS_DERIVED_COLUMN = """
SELECT EXISTS (
  SELECT 1 FROM information_schema.columns
  WHERE table_schema = 'map_bounds' AND table_name = 'compilation'
    AND column_name = 'is_derived'
)
"""


class CompilationAssemblyMode(Migration):
    """`assembly_mode` becomes `topological` | `mosaic` (was `layered` | `disjoint`).

    The axis was always whether members overlap; what the new words add is the
    consequence. Overlap is what the topology exists to settle, so a
    *topological* compilation's members are found by face identity. A *mosaic*
    partitions its territory, so a member's extent is its footprint and its
    content is the compilation's content inside it -- no faces of its own, no
    noding, until something topological places it directly.

    `is_documentary` is retired: it meant "member of a compilation whose content
    was ingested", which conflated where the polygons live with how members are
    resolved. `is_mosaic_member` says the second thing only, and a nested virtual
    mosaic (South Carolina's two maps as one unit under SGMC) needs exactly that.

    `content` becomes `is_derived`, the one fact worth recording: the polygons
    are a cache that `materialize` wrote. `ingested` stops being stored -- it is
    "holds polygons and is not derived", read through `map_bounds.content()` --
    so it can no longer drift, and the manual `compilations content` command goes.
    """

    name = "compilation-assembly-mode-vocabulary"
    subsystem = "maps"
    description = (
        "assembly_mode: layered/disjoint -> topological/mosaic; content -> is_derived"
    )
    readiness_state = "ga"
    destructive = False

    preconditions = [
        lambda db: (
            _scalar(db, _OLD_ROWS)
            or not _scalar(db, _NEW_CONSTRAINT)
            or _scalar(db, _OLD_PREDICATE)
            or _scalar(db, _CONTENT_COLUMN)
            or not _scalar(db, _IS_DERIVED_COLUMN)
        ),
    ]
    postconditions = [
        lambda db: not _scalar(db, _OLD_ROWS),
        lambda db: _scalar(db, _NEW_CONSTRAINT),
        lambda db: not _scalar(db, _OLD_PREDICATE),
        lambda db: not _scalar(db, _CONTENT_COLUMN),
        lambda db: _scalar(db, _IS_DERIVED_COLUMN),
    ]

    def apply(self, database: Database):
        database.run_sql(
            """
            ALTER TABLE map_bounds.compilation
              DROP CONSTRAINT IF EXISTS compilation_assembly_mode_check;

            UPDATE map_bounds.compilation
            SET assembly_mode = CASE assembly_mode
              WHEN 'layered' THEN 'topological'
              WHEN 'disjoint' THEN 'mosaic'
              ELSE assembly_mode END
            WHERE assembly_mode IN ('layered', 'disjoint');

            ALTER TABLE map_bounds.compilation
              ALTER COLUMN assembly_mode SET DEFAULT 'topological';

            ALTER TABLE map_bounds.compilation
              ADD CONSTRAINT compilation_assembly_mode_check
              CHECK (assembly_mode IN ('topological', 'mosaic'));

            -- Replaced by `is_mosaic_member`; the fixture defines the new
            -- predicates, and `schema sync` cannot drop the old one.
            DROP FUNCTION IF EXISTS map_bounds.is_documentary(integer);

            -- `content` -> `is_derived`. `ingested` is no longer stored: it is
            -- "holds polygons and is not derived" (`map_bounds.content`).
            ALTER TABLE map_bounds.compilation
              ADD COLUMN IF NOT EXISTS is_derived boolean NOT NULL DEFAULT false;

            UPDATE map_bounds.compilation SET is_derived = true
            WHERE content = 'derived';

            -- `compilation_sync` reads the column; the fixture below recreates
            -- it over `is_derived`.
            DROP VIEW IF EXISTS map_bounds.compilation_sync;
            ALTER TABLE map_bounds.compilation DROP COLUMN IF EXISTS content;
            """
        )
        # Restore the view and define the new predicates now rather than at the
        # next `schema sync`, so nothing reads a half-migrated schema in between.
        database.run_sql(FIXTURE)


def _scalar(db: Database, sql: str) -> bool:
    return db.run_query(sql).scalar() is True
