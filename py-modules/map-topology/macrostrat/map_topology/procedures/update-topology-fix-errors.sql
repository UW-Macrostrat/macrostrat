/* Re-attempt a map's errored map_topo rows at a (typically reduced) snap
   tolerance. update_topogeom returns NULL on success and clears the error, or
   the error text on failure. */
WITH update AS (
  SELECT
    map_bounds.update_topogeom(m, :tolerance) res
  FROM map_bounds.map_topo m
  WHERE map_id = :map_id
    AND topo IS NULL
    AND topology_error IS NOT NULL
  LIMIT :batch_size
)
SELECT
  -- Rows recovered this pass
  count(*) FILTER (WHERE m.res IS NULL) updated,
  -- Rows that still failed
  count(*) FILTER (WHERE m.res IS NOT NULL) failed,
  array_remove(array_agg(m.res), null) errors
FROM update m;
