/* Everything covering a point, at every level of the unit graph.

   Deliberately unfiltered: rather than choosing a level server-side, this returns
   the constituent map, the unit it is presented as, and flags describing each, so
   a client can filter or group however it needs. `is_composite` marks a row whose
   map is assembled from others; `is_materialized` marks one that holds polygons
   of its own and is therefore where resolution stops.
*/
WITH loc AS (
  SELECT ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) AS geometry
)
SELECT
    mp.source_id,
    array_to_string(mp.priority_path, '.') AS priority,
    mp.priority_path,
    ml.slug map_layer,
    ml.name layer_name,
    s.name,
    s.slug,
    s.scale,
    -- The unit this map is presented as at this level: the nearest compilation
    -- above it that is not a structural layer. Equal to the map itself when it
    -- stands alone.
    mp.via AS unit_id,
    v.slug AS unit,
    v.name AS unit_name,
    mp.via IS DISTINCT FROM mp.source_id AS is_constituent,
    EXISTS (
      SELECT 1 FROM map_bounds.compilation_member cm
      WHERE cm.compilation_id = mp.via
    ) AS is_composite,
    map_bounds.holds_polygons(mp.source_id) AS is_materialized,
    map_bounds.holds_polygons(mp.via) AS unit_is_materialized,
    map_bounds.is_served_layer(mp.via) AS unit_is_layer,
    mf.id map_face_id,
    uf.id unit_face_id
FROM map_bounds.map_priority mp
JOIN map_bounds.map_layer ml
  ON ml.id = mp.map_layer
JOIN map_bounds.map_area ma
  ON ma.source_id = mp.source_id
JOIN maps.sources s ON s.source_id = ma.source_id
LEFT JOIN maps.sources v ON v.source_id = mp.via
JOIN loc ON ST_Intersects(ma.geometry, loc.geometry)
LEFT JOIN map_bounds_topology.map_face mf
  ON mf.map_id = mp.source_id
  AND mf.map_layer = mp.map_layer
  AND ST_Intersects(mf.geometry, loc.geometry)
-- The merged face for the unit, where the unit is a compilation.
LEFT JOIN map_bounds_topology.map_face uf
  ON uf.map_id = mp.via
  AND uf.map_layer = mp.map_layer
  AND uf.map_id IS DISTINCT FROM mp.source_id
  AND ST_Intersects(uf.geometry, loc.geometry)
WHERE ::where_clauses
ORDER BY mp.priority_path DESC;
