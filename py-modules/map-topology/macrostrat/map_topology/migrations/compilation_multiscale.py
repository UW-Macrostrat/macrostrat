"""`multiscale` compilations: `carto` as one source, zoom bands in one table."""

from macrostrat.database import Database
from macrostrat.schema_management import Migration, exists

from ..bounds.compile import compile_bounds
from ..bounds.layers import layer_bounds, seed_layer_openings

# `strpos`, not LIKE: a bare `%` in SQL run through SQLAlchemy reads as a bind.
_CONSTRAINT_ALLOWS_MULTISCALE = """
SELECT EXISTS (
  SELECT 1 FROM pg_constraint
  WHERE conrelid = 'map_bounds.compilation'::regclass
    AND conname = 'compilation_assembly_mode_check'
    AND strpos(pg_get_constraintdef(oid), 'multiscale') > 0
)
"""

_IS_MULTISCALE = """
SELECT coalesce(
  (SELECT c.assembly_mode = 'multiscale'
   FROM maps.sources s
   LEFT JOIN map_bounds.compilation c ON c.source_id = s.source_id
   WHERE s.slug = :slug),
  :absent_ok
)
"""


def _constraint_allows_multiscale(db: Database) -> bool:
    return db.run_query(_CONSTRAINT_ALLOWS_MULTISCALE).scalar() is True


def _is_multiscale(slug: str, absent_ok: bool = False):
    """Whether `slug` is a multiscale compilation. `absent_ok` says what a
    missing row means: `carto-v1` only exists where legacy carto was frozen."""

    def check(db: Database) -> bool:
        return (
            db.run_query(_IS_MULTISCALE, dict(slug=slug, absent_ok=absent_ok)).scalar()
            is True
        )

    return check


def _multiscale_bounds_built(db: Database) -> bool:
    return all(l.complete for l in layer_bounds(db) if l.is_multiscale)


class CompilationMultiscale(Migration):
    """Add the `multiscale` assembly mode and make `carto` a compilation.

    A multiscale compilation's members are alternatives by scale: a request at
    a zoom is answered by the member whose band contains it, read from the new
    `map_bounds.scale_band` table (the one home for the 3/6/9 thresholds).
    `carto` becomes a `maps.sources` row over `tiny`, `carto-small`,
    `carto-medium` and `carto-large`, so the served map can be named on the
    same routes as any other source, and the `carto-v2` string retires.

    `carto-v1`, the frozen snapshot, is given the same shape: multiscale over its
    four tiers (it lacked `tiny-v1`), with the priorities that meant nothing
    there cleared.

    The fixture file carries the seed rows (the row, its membership, the members'
    `scale`), so this migration only widens the constraint the fixture cannot
    alter on an existing table, re-syncs the chunk, fixes the snapshot and gives
    the multiscale compilations their `world` bounds.
    """

    name = "compilation-multiscale"
    owner = None  # its own `apply`, written for the connector's privileges
    subsystem = "maps"
    description = "`multiscale` assembly mode; `carto` as a compilation"
    readiness_state = "ga"
    depends_on = ["compilation-assembly-mode-vocabulary", "compilation-layer-bounds"]
    load_sql_files = False
    # Adds rows and widens a constraint; removes nothing and rewrites no map.
    destructive = False
    sync_chunks = ["map-topology"]

    preconditions = [
        exists("map_bounds", "compilation", "compilation_member"),
        lambda db: (
            not (
                _constraint_allows_multiscale(db)
                and _is_multiscale("carto")(db)
                and _is_multiscale("carto-v1", absent_ok=True)(db)
                and _multiscale_bounds_built(db)
            )
        ),
    ]
    postconditions = [
        _constraint_allows_multiscale,
        _is_multiscale("carto"),
        _is_multiscale("carto-v1", absent_ok=True),
        _multiscale_bounds_built,
    ]

    def apply(self, database: Database):
        database.run_sql(
            """
            ALTER TABLE map_bounds.compilation
              DROP CONSTRAINT IF EXISTS compilation_assembly_mode_check;
            ALTER TABLE map_bounds.compilation
              ADD CONSTRAINT compilation_assembly_mode_check
              CHECK (assembly_mode IN ('topological', 'mosaic', 'multiscale'));
            """
        )
        # The chunk re-sync declared above runs after `apply`, so the seed rows
        # are applied here too: everything in the fixture is idempotent.
        database.run_fixtures(self.fixture_path())
        database.run_sql(
            """
            UPDATE map_bounds.compilation c
            SET assembly_mode = 'multiscale'
            WHERE c.source_id = map_bounds.source_id('carto-v1');

            INSERT INTO map_bounds.compilation_member (compilation_id, member_id, priority)
            SELECT c.source_id, m.source_id, NULL
            FROM maps.sources c
            JOIN maps.sources m ON m.slug = 'tiny-v1'
            WHERE c.slug = 'carto-v1'
            ON CONFLICT (compilation_id, member_id) DO NOTHING;

            UPDATE map_bounds.compilation_member cm
            SET priority = NULL
            WHERE cm.compilation_id = map_bounds.source_id('carto-v1')
              AND cm.priority IS NOT NULL;
            """
        )
        database.session.commit()

        areas, openings = seed_layer_openings(database)
        # A compilation that had members before it was multiscale was given a
        # `compile` opening by `compile_bounds`, which the seed respects. A
        # multiscale compilation is global by definition, so it opens with `world`.
        database.run_sql(
            """
            UPDATE map_bounds.boundary_op o
            SET operation = 'world', geometry = NULL, parameters = jsonb_build_object()
            FROM map_bounds.compilation c
            WHERE c.source_id = o.source_id
              AND c.assembly_mode = 'multiscale'
              AND o.position = 0
              AND o.operation = 'compile'
            """
        )
        database.session.commit()
        print(f"Seeded {areas} boundary rows and {openings} openings")
        ids = [l.source_id for l in layer_bounds(database) if l.is_multiscale]
        for res in compile_bounds(database, force=True, only=ids):
            if res.error:
                print(f"  {res.slug}: {res.error}")
            elif res.built:
                print(f"  {res.slug} -- {res.area_km:,.0f} km²")

    @staticmethod
    def fixture_path():
        from pathlib import Path

        return Path(__file__).parent.parent / "fixtures" / "04-compilation-tables.sql"
