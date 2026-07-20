WITH loc AS (
  SELECT ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) AS geometry
)
SELECT
    mp.map_id source_id,
    mp.priority,
    ml.slug map_layer,
    ml.name layer_name,
    s.name,
    s.slug,
    s.scale,
    mf.id map_face_id
FROM map_bounds.map_priority mp
JOIN map_bounds.map_layer ml
  ON ml.id = mp.map_layer
JOIN map_bounds.map_area ma
  ON ma.id = mp.map_id
JOIN maps.sources s ON s.source_id = ma.id
JOIN loc ON ST_Intersects(ma.geometry, loc.geometry)
LEFT JOIN map_bounds_topology.map_face mf
  ON mf.map_id = ma.id
  AND mf.map_layer = coalesce(map_bounds.layer_id(:map_layer), -1)
  AND ST_Intersects(mf.geometry, loc.geometry)
WHERE ::where_clauses
ORDER BY mp.priority DESC;
