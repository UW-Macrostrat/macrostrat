from macrostrat.database import Database
from macrostrat.schema import Migration, exists

# Invalid only because some vertices sit on the far side of the antimeridian.
_MISWRAPPED = """
SELECT EXISTS (
  SELECT 1 FROM macrostrat.refs
  WHERE NOT ST_IsValid(rgeom)
    AND ST_XMax(rgeom) - ST_XMin(rgeom) > 180
    AND ST_IsValid(ST_ShiftLongitude(rgeom))
)
"""


def _miswrapped_refs(db: Database) -> bool:
    """A reference geometry crosses the antimeridian the long way round."""
    return db.run_query(_MISWRAPPED).scalar()


class RefGeometryAntimeridianMigration(Migration):
    name = "ref-geometry-antimeridian"
    subsystem = "core"
    description = """
    Split reference geometries that cross the antimeridian the long way round
    """
    readiness_state = "ga"
    destructive = True

    preconditions = [exists("macrostrat", "refs"), _miswrapped_refs]
    postconditions = [lambda db: not _miswrapped_refs(db)]
