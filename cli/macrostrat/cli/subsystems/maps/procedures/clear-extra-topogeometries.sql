/**
  Get rid of orphaned topogeometries in the map_bounds.map_topo table.
  This is required as deleting topogeometry rows does not delete the
  underlying topogeometry primitives.

  The clearTopoGeom procedure can be used instead of this one to
  remove old elements when a topogeometry is modified.
 */

WITH lyr AS (
  SELECT (topology.FindLayer('map_bounds.map_topo', 'topo')).*
), to_delete AS (
  SELECT topogeo_id
  FROM map_bounds_topology.relation r
  WHERE layer_id = (SELECT layer_id FROM lyr)
  EXCEPT
  SELECT (topo).id
  FROM map_bounds.map_topo
  WHERE topo IS NOT NULL
), deleted AS (
  DELETE FROM map_bounds_topology.relation
  WHERE topogeo_id IN (SELECT topogeo_id FROM to_delete)
  RETURNING *
)
SELECT count(*) FROM deleted;
