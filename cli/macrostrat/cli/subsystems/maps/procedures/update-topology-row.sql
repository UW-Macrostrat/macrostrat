WITH update AS (
  SELECT
    map_bounds.update_topogeom(m) res
  FROM map_bounds.map_topo m
  WHERE source_id = :source_id
    AND topo IS NULL
    AND topology_error IS NULL
  LIMIT :batch_size
)
SELECT
  -- Count of successful updates
  count(m.res IS NULL) updated,
  -- Count of failed updates
  count(m.res IS NOT NULL) failed,
  (
    SELECT count(*) n
    FROM map_bounds.map_topo
    WHERE source_id = :source_id
      AND topo IS NULL
      AND topology_error IS NULL
   )-count(*)  remaining,
  array_remove(array_agg(m.res), null) errors
FROM update m;
