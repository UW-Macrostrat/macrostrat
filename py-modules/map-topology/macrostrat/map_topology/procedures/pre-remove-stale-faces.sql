/** Take maps about to be re-noded out of the solved map faces, so the primitives
  only those map faces held can be removed before anything is noded over them.

  Emptying a map's topogeometry does not remove its old outline: the map faces
  solved against it still hold the faces on either side, so `RemoveUnusedPrimitives`
  keeps the edges, and the new outline is noded across the old one -- 648 faces
  where 35 were needed, under one re-buffered Japan sheet on development.

  The faces released are those the map won in each layer that solves it, and their
  neighbours across an edge, which the old outline also bounds. They leave every
  map face of the layer holding them -- the map's own, its neighbours', unit
  faces -- and are queued for the dissolve. No `map_face` row is deleted: one left
  with no faces gets `topo = NULL`, which the solver and identity marking skip, and
  serves its stale geometry until the dissolve is done (`update_maps` deletes it).

  No ON COMMIT DROP: statements here are committed individually. */
DROP TABLE IF EXISTS _restart;
CREATE TEMP TABLE _restart AS
SELECT unnest(CAST(:map_ids AS integer[])) AS map_id;

/* The map's own topogeometry holds the old outline too. */
UPDATE map_bounds.map_area
SET topo = NULL, geometry_hash = NULL, topology_error = NULL
WHERE source_id IN (SELECT map_id FROM _restart)
  AND (topo IS NOT NULL OR geometry_hash IS NOT NULL);

DROP TABLE IF EXISTS _won;
CREATE TEMP TABLE _won AS
SELECT DISTINCT x.map_id, f.map_layer, r.element_id AS face_id
FROM _restart x
JOIN map_bounds.map_priority mp ON mp.map_id = x.map_id
JOIN map_bounds_topology.map_face f
  ON f.map_id = x.map_id
 AND f.map_layer = mp.map_layer
JOIN map_bounds_topology.relation r
  ON r.layer_id = (f.topo).layer_id
 AND r.topogeo_id = (f.topo).id
 AND r.element_type = 3;
ANALYZE _won;

/* One join per side of the edge, so each can use its face index. */
DROP TABLE IF EXISTS _released;
CREATE TEMP TABLE _released AS
SELECT map_id, map_layer, face_id FROM _won
UNION
SELECT w.map_id, w.map_layer, e.right_face
FROM _won w JOIN map_bounds_topology.edge_data e ON e.left_face = w.face_id
WHERE e.right_face <> 0
UNION
SELECT w.map_id, w.map_layer, e.left_face
FROM _won w JOIN map_bounds_topology.edge_data e ON e.right_face = w.face_id
WHERE e.left_face <> 0;
CREATE INDEX ON _released (face_id, map_layer);
ANALYZE _released;

INSERT INTO map_bounds_topology.dirty_face (id, map_layer)
SELECT DISTINCT face_id, map_layer FROM _released
ON CONFLICT DO NOTHING;

DROP TABLE IF EXISTS _touched;
CREATE TEMP TABLE _touched AS
WITH gone AS (
  DELETE FROM map_bounds_topology.relation r
  USING map_bounds_topology.map_face f, _released x
  WHERE r.layer_id = map_bounds_topology.__map_face_layer_id()
    AND r.element_type = 3
    AND r.element_id = x.face_id
    AND f.map_layer = x.map_layer
    AND (f.topo).id = r.topogeo_id
    AND (f.topo).layer_id = r.layer_id
  RETURNING r.topogeo_id
)
SELECT DISTINCT topogeo_id FROM gone;

DELETE FROM map_bounds_topology.face_identity fi
USING _released x
WHERE fi.face_id = x.face_id AND fi.map_layer = x.map_layer;

UPDATE map_bounds_topology.map_face f
SET topo = NULL
WHERE (f.topo).id IN (SELECT topogeo_id FROM _touched)
  AND NOT EXISTS (
    SELECT 1 FROM map_bounds_topology.relation r
    WHERE r.layer_id = (f.topo).layer_id AND r.topogeo_id = (f.topo).id
  );

/* Boxes first: removing primitives merges and deletes the faces they come from. */
DROP TABLE IF EXISTS _boxes;
CREATE TEMP TABLE _boxes AS
SELECT x.map_id, ST_SetSRID(ST_Extent(f.mbr)::geometry, 4326) AS box
FROM _released x
JOIN map_bounds_topology.face f ON f.face_id = x.face_id
GROUP BY x.map_id;

/* Read by the caller for its summary. */
SELECT
  (SELECT count(*) FROM _boxes) AS maps,
  (SELECT count(*) FROM (SELECT DISTINCT face_id, map_layer FROM _released) x) AS released,
  (SELECT count(*) FROM _touched) AS map_faces_touched,
  (
    SELECT coalesce(sum(topology.RemoveUnusedPrimitives('map_bounds_topology', box)), 0)
    FROM _boxes
  ) AS primitives_removed;
