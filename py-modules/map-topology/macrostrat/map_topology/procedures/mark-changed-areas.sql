/** Mark changed maps to revisit in topology construction */
WITH elements AS (
  SELECT t.map_id,
    sum(array_length(topology.GetTopoGeomElementArray(t.topo), 1)) AS topo_count
  FROM map_bounds.map_topo t
  GROUP BY t.map_id
), counts AS (
  SELECT
    map_id,
    topo_count,
    array_length(topology.GetTopoGeomElementArray(ma.topo), 1) AS area_count
  FROM elements
  JOIN map_bounds.map_area ma ON ma.id = elements.map_id
)
UPDATE map_bounds.map_area
SET geometry_hash = NULL
FROM counts
WHERE map_area.id = counts.map_id
  AND counts.topo_count != counts.area_count;
