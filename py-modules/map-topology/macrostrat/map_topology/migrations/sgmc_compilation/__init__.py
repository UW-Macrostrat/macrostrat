"""Recover SGMC's constituent maps as documentary members."""

from macrostrat.database import Database
from macrostrat.schema_management import Migration

SGMC = 133

_STAGING_EXISTS = """
SELECT to_regclass('sources.sgmc_polygons') IS NOT NULL
"""

_ALREADY_DONE = """
SELECT EXISTS (
  SELECT 1 FROM map_bounds.compilation_member WHERE compilation_id = 133
)
"""

_SGMC_INTACT = """
SELECT (SELECT count(*) FROM maps.polygons WHERE source_id = 133) > 0
   AND (SELECT topo IS NOT NULL FROM map_bounds.map_area WHERE source_id = 133)
"""


class SGMCCompilation(Migration):
    """Declare SGMC a compilation of the 65 published maps it was compiled from.

    SGMC arrived as one `maps.sources` row holding 312,286 polygons for the
    conterminous US, which is the one thing it demonstrably is not: the USGS
    assembled it from state maps, and the structured provenance survived
    ingestion in `sources.sgmc_polygons` (`ref_id`, `reference`, `digital_ur`),
    joinable to `maps.polygons` by `orig_id::integer = _pkid` for every row.

    The members are **documentary**. SGMC keeps its polygons and its boundary;
    the members record where they came from, as sources with citations, URLs and
    footprints. They are never noded, so this costs nothing in the topology --
    the alternative, splitting the polygons out and giving each member real
    linework, measures at +30% on total topology linework (983,404 simplified
    boundary points against `map_topo`'s current 3,308,335) and needs a
    coverage-aware simplifier we do not have: `ST_CoverageSimplify` requires
    GEOS 3.12+ and the image ships 3.11.1.

    Reversible, and deliberately additive: promoting the members to real ones
    later means moving polygons and noding boundaries, not undoing this.
    """

    name = "sgmc-documentary-compilation"
    subsystem = "maps"
    description = "Recover SGMC's 65 constituent maps as documentary members"
    readiness_state = "ga"
    destructive = False

    preconditions = [
        # Without the staging table there is no provenance to recover, and a
        # migration that silently does nothing is worse than one that does not run.
        lambda db: _scalar(db, _STAGING_EXISTS),
        lambda db: _scalar(db, _SGMC_INTACT),
        lambda db: not _scalar(db, _ALREADY_DONE),
    ]
    postconditions = [
        lambda db: _scalar(db, _ALREADY_DONE),
        # The point of the exercise: SGMC keeps everything it had.
        lambda db: _scalar(db, _SGMC_INTACT),
    ]


def _scalar(db: Database, sql: str) -> bool:
    return db.run_query(sql).scalar() is True
