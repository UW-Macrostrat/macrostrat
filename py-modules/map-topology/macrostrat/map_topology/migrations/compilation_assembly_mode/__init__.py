"""Name compilations by how their members' extents are settled."""

from psycopg.errors import UndefinedTable
from sqlalchemy.exc import ProgrammingError

from macrostrat.database import Database
from macrostrat.schema_management import Migration, exists

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

    The stored `content` column goes. Whether a compilation's polygons are a
    cache is read off the rows themselves (`map_bounds.is_materialized`: it holds
    polygons and owns no legend entry, because `materialize` links each polygon to
    its member's), so it can no longer drift, and the manual `compilations
    content` command goes. (An intermediate `is_derived` boolean existed between
    2026-09-17 and 2026-09-24; the declarative schema drops it.)
    """

    name = "compilation-assembly-mode-vocabulary"
    subsystem = "maps"
    description = (
        "assembly_mode: layered/disjoint -> topological/mosaic; drop stored content"
    )
    readiness_state = "ga"
    destructive = False
    # Restores `compilation_sync` and defines the new predicates straight away,
    # so nothing reads a half-migrated schema until the next `schema sync`.
    sync_chunks = ["map-topology"]

    # The table comes from the compilation schema; until that has been applied
    # there is nothing to migrate, and the checks below would read its absence
    # as an old vocabulary.
    preconditions = [
        exists("map_bounds", "compilation"),
        lambda db: (
            _scalar(db, _OLD_ROWS)
            or not _scalar(db, _NEW_CONSTRAINT)
            or _scalar(db, _OLD_PREDICATE)
            or _scalar(db, _CONTENT_COLUMN)
        ),
    ]
    postconditions = [
        lambda db: not _scalar(db, _OLD_ROWS),
        lambda db: _scalar(db, _NEW_CONSTRAINT),
        lambda db: not _scalar(db, _OLD_PREDICATE),
        lambda db: not _scalar(db, _CONTENT_COLUMN),
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

            -- Replaced by `is_mosaic_member`; the chunk defines the new
            -- predicates, and `schema sync` cannot drop the old one.
            DROP FUNCTION IF EXISTS map_bounds.is_documentary(integer);

            -- Whether polygons are a cache is no longer stored: it is read off
            -- the legend links (`map_bounds.is_materialized`). `compilation_sync`
            -- reads the column; syncing the chunk recreates it.
            DROP VIEW IF EXISTS map_bounds.compilation_sync;
            ALTER TABLE map_bounds.compilation DROP COLUMN IF EXISTS content;
            """
        )


def _scalar(db: Database, sql: str) -> bool:
    try:
        return db.run_query(sql).scalar() is True
    except ProgrammingError:
        return False
