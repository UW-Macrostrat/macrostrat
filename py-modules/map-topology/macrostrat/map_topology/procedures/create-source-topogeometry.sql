WITH elements AS (
  SELECT
    (topo).*
  FROM map_bounds.map_topo
  WHERE map_id = :map_id
),
face_ids AS (
  SELECT r.element_id face_id
  FROM map_bounds_topology.relation r
  JOIN elements t
  ON t.layer_id = r.layer_id
    AND t.id = r.topogeo_id
    AND t.type = r.element_type
    AND r.element_type = 3
  GROUP BY r.element_id
),
topo_elements AS (
  SELECT array_agg(ARRAY[face_id, 3]) topo_element_array
  FROM face_ids
),
layer_info AS (
  SELECT layer_id
  FROM topology.layer
  WHERE schema_name = 'map_bounds'
    AND table_name = 'map_area'
    AND feature_column = 'topo'
),
topogeo AS (
  SELECT topology.createTopoGeom('map_bounds_topology', 3, (
    SELECT layer_id
    FROM layer_info
  ), topo_element_array) AS topo
  FROM topo_elements
)
UPDATE map_bounds.map_area
SET
  topo = topogeo.topo,
  geometry_hash = md5(ST_AsBinary(map_area.geometry))::uuid
FROM topogeo
WHERE map_area.id = :map_id



