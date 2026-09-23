/** Mark changed maps to revisit in topology construction */
WITH elements AS (
  SELECT t.source_id,
    sum(array_length(topology.GetTopoGeomElementArray(t.topo), 1)) AS topo_count
  FROM map_bounds.map_topo t
  GROUP BY t.source_id
), counts AS (
  SELECT
    ma.source_id,
    topo_count,
    array_length(topology.GetTopoGeomElementArray(ma.topo), 1) AS area_count
  FROM elements
  JOIN map_bounds.map_area ma ON ma.source_id = elements.source_id
)
/* An element-count mismatch means the *assembly* is stale, not the parts, so
   clear the assembled topogeometry rather than the parts' provenance hash.
   `create-source-topogeometry` rebuilds it from the parts. */
UPDATE map_bounds.map_area
SET topo = NULL
FROM counts
WHERE map_area.source_id = counts.source_id
  AND counts.topo_count != counts.area_count;
