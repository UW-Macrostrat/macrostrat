"""Adopt the topogeometries an earlier code path built, instead of re-noding."""

from macrostrat.database import Database
from macrostrat.schema_management import Migration

#: Maps whose topogeometry was built from their current bounds, by the stamp the
#: library set. The hash is computed once per row, in a materialized CTE: inline
#: in a join it would be re-evaluated per piece.
_CURRENT_MAPS = """
WITH current AS MATERIALIZED (
  SELECT a.source_id, a.geometry_hash
  FROM map_bounds.map_area a
  WHERE a.topo IS NOT NULL
    AND a.geometry_hash = md5(ST_AsBinary(a.geometry))::uuid
    AND NOT (
      map_bounds.is_compilation(a.source_id)
      AND NOT map_bounds.is_mosaic(a.source_id)
    )
)
"""

_UNADOPTED_PIECES = (
    _CURRENT_MAPS
    + """
SELECT count(*) FROM map_bounds.map_topo t
JOIN current c ON c.source_id = t.source_id
WHERE t.bounds_hash IS NULL
"""
)

_COMPILATION_TOPOS = """
SELECT count(*) FROM map_bounds.map_area a
WHERE a.topo IS NOT NULL
  AND map_bounds.is_compilation(a.source_id)
  AND NOT map_bounds.is_mosaic(a.source_id)
"""


def _has_column(table: str, column: str):
    def check(db: Database) -> bool:
        return (
            db.run_query(
                """
                SELECT EXISTS (
                  SELECT 1 FROM information_schema.columns
                  WHERE table_schema = 'map_bounds'
                    AND table_name = :table AND column_name = :column
                )
                """,
                dict(table=table, column=column),
            ).scalar()
            is True
        )

    return check


def _count(sql: str):
    def check(db: Database) -> int:
        return db.run_query(sql).scalar()

    return check


class MapTopoAdoptMigration(Migration):
    """Mark the pieces of every noded map as noded from its current bounds, and
    drop the topogeometries compilations no longer have.

    Piecewise noding keeps `map_topo` as a record of the pieces a map's
    topogeometry was noded from, tagged with the bounds they were cut from. The
    columns arrived empty on an existing database, so every piece read as
    pending and `topo update` would have re-noded every map from scratch --
    days of work to rebuild topogeometries that are already exactly what the
    new code would build: one level-0 topogeometry per map over the same
    primitives.

    So where the library's stamp says a map's topogeometry reflects its current
    bounds, its pieces are adopted: `bounds_hash` set to that stamp, `noded`
    where no error was recorded. Pieces with a recorded error stay failed, for
    `topo errors --fix`. A map the new code has already reset (its pieces carry a
    `bounds_hash`) is left to resume.

    A materialized compilation had a topogeometry under the old code; identity
    now resolves through its members and it has none. Setting `topo` to NULL
    releases its primitives and marks the faces it covered dirty, via the
    library's trigger.

    Data only, so it runs after `schema apply` has added the columns.
    """

    name = "map-topo-adopt"
    subsystem = "maps"
    description = "Adopt existing topogeometries as piecewise-noded"
    readiness_state = "ga"
    destructive = True
    depends_on = ["map-topo-pieces"]

    preconditions = [
        _has_column("map_topo", "bounds_hash"),
        _has_column("map_topo", "noded"),
        lambda db: _count(_UNADOPTED_PIECES)(db) > 0
        or _count(_COMPILATION_TOPOS)(db) > 0,
    ]
    postconditions = [
        _has_column("map_topo", "bounds_hash"),
        lambda db: _count(_UNADOPTED_PIECES)(db) == 0,
        lambda db: _count(_COMPILATION_TOPOS)(db) == 0,
    ]

    def apply(self, database: Database):
        n = database.run_query(
            _CURRENT_MAPS
            + """
            UPDATE map_bounds.map_topo t
            SET bounds_hash = c.geometry_hash,
                noded = (t.topology_error IS NULL)
            FROM current c
            WHERE t.source_id = c.source_id
              AND t.bounds_hash IS NULL
            """
        ).rowcount
        m = database.run_query(
            """
            UPDATE map_bounds.map_area a
            SET topo = NULL, geometry_hash = NULL, topology_error = NULL
            WHERE a.topo IS NOT NULL
              AND map_bounds.is_compilation(a.source_id)
              AND NOT map_bounds.is_mosaic(a.source_id)
            """
        ).rowcount
        database.session.commit()
        print(f"Adopted {n} pieces; cleared {m} compilation topogeometries")
