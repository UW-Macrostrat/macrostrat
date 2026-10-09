"""Seed map boundaries from the legacy `rgeom`, before `topo update` unions them."""

from macrostrat.database import Database
from macrostrat.schema_management import Migration, exists

from ..bounds.build import OPS_HASH

#: Maps `copy-all-maps` would seed that hold an `rgeom` to adopt instead. None can
#: be the trigger's mirror: `sync_source_rgeom` writes only maps with a `map_area`.
_CANDIDATE = """
  s.is_finalized
  AND s.status_code = 'active'
  AND s.scale = ANY (enum_range(NULL::maps.map_scale)::text[])
  AND s.rgeom IS NOT NULL
  AND NOT ST_IsEmpty(s.rgeom)
  AND NOT EXISTS (SELECT 1 FROM map_bounds.map_area a WHERE a.id = s.source_id)
  AND NOT EXISTS (SELECT 1 FROM map_bounds.boundary_op o WHERE o.source_id = s.source_id)
"""

#: `boundary_op` references `map_area`, so the boundary is written first.
_ADOPTED_AREAS = f"""
INSERT INTO map_bounds.map_area (id, geometry, area_km, map_layer)
SELECT s.source_id, g.geometry,
       ST_Area(ST_Segmentize(g.geometry, 90)::geography) / 1e6,
       map_bounds.barrier_layer()
FROM maps.sources s
CROSS JOIN LATERAL (
  SELECT ST_Multi(ST_CollectionExtract(ST_MakeValid(s.rgeom), 3)) AS geometry
) g
WHERE {_CANDIDATE}
  AND NOT ST_IsEmpty(g.geometry)
RETURNING id
"""

_ADOPT_OPENINGS = """
INSERT INTO map_bounds.boundary_op (source_id, position, operation, geometry, parameters, note)
SELECT a.id, 0, 'adopt', a.geometry,
       jsonb_build_object('layer', 'maps.sources.rgeom'),
       'Adopted from the legacy rgeom rather than unioned from features'
FROM map_bounds.map_area a
WHERE a.id = ANY(:ids)
"""

_STAMP_BUILT = f"""
UPDATE map_bounds.map_area a
SET ops_hash = (SELECT {OPS_HASH} FROM map_bounds.boundary_op o WHERE o.source_id = a.id)
WHERE a.id = ANY(:ids)
"""


def _nothing_to_adopt(db: Database) -> bool:
    """No map without bounds holds a legacy `rgeom` to adopt."""
    query = f"SELECT NOT EXISTS (SELECT 1 FROM maps.sources s WHERE {_CANDIDATE})"
    return db.run_query(query).scalar()


class MapAreaFromRgeom(Migration):
    """Open each unbounded map with its `rgeom`, as an `adopt` operation.

    `copy-all-maps` would otherwise union every map's polygons on a database's
    first `topo update`. The stamped `ops_hash` keeps `bounds build --all` from
    re-unioning them.
    """

    name = "map-area-from-rgeom"
    subsystem = "maps"
    description = "Seed map boundaries from the legacy rgeom"
    readiness_state = "ga"
    depends_on = ["map-bounds-source-id"]
    destructive = False

    preconditions = [exists("map_bounds", "map_area", "boundary_op")]
    postconditions = [_nothing_to_adopt]

    def apply(self, database: Database):
        ids = [r.id for r in database.run_query(_ADOPTED_AREAS).all()]
        if ids:
            database.run_query(_ADOPT_OPENINGS, dict(ids=ids))
            database.run_query(_STAMP_BUILT, dict(ids=ids))
        database.session.commit()
