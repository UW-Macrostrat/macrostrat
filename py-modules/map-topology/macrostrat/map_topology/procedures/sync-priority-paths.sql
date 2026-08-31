/** Rebuild the flattened priority paths that identity resolution orders by.

  Three edge kinds compose into a single path:

    layer -> layer   `map_layer_composition`
    layer -> map     `map_priority` (the authored rows)
    map   -> map     `map_composition`

  The walk stops at a map that holds its own polygons. A *virtual* compilation is
  descended through, so a face resolves to whoever actually has the geometry;
  a *materialized* one is a leaf, which is also what keeps a compilation's
  constituents out of the topology without a filter of their own.
*/

DELETE FROM map_bounds.map_priority WHERE derived;

WITH RECURSIVE layer_paths AS (
  SELECT ml.id AS root, ml.id AS layer_id, ARRAY[]::integer[] AS path
  FROM map_bounds.map_layer ml
  UNION ALL
  SELECT lp.root, c.member_id, lp.path || c.priority
  FROM layer_paths lp
  JOIN map_bounds.map_layer_composition c
    ON c.parent_id = lp.layer_id
),
/** Enter the map world wherever a layer has maps assigned directly. */
seeds AS (
  SELECT lp.root, mp.source_id, lp.path || coalesce(mp.priority, 0) AS path
  FROM layer_paths lp
  JOIN map_bounds.map_priority mp
    ON mp.map_layer = lp.layer_id
   AND NOT mp.derived
),
map_paths AS (
  SELECT root, source_id, path FROM seeds
  UNION ALL
  SELECT mp.root, mc.member_id, mp.path || coalesce(mc.priority, 0)
  FROM map_paths mp
  JOIN map_bounds.map_composition mc
    ON mc.compilation_id = mp.source_id
  WHERE NOT map_bounds.holds_polygons(mp.source_id)
),
/** A map can be reachable under one root by more than one route -- directly in a
  layer and again through a compilation, which is the state a half-migrated
  compilation is in. The winning route is the one that would win anyway. */
leaves AS (
  SELECT DISTINCT ON (root, source_id) root, source_id, path
  FROM map_paths
  WHERE map_bounds.holds_polygons(source_id)
  ORDER BY root, source_id, path DESC
)
INSERT INTO map_bounds.map_priority (map_layer, source_id, priority_path, derived)
SELECT root, source_id, path, true
FROM leaves
/** An authored row keeps `derived = false` and simply gains its path; only rows
  that did not already exist are owned by the sync. */
ON CONFLICT (map_layer, source_id) DO UPDATE
  SET priority_path = EXCLUDED.priority_path;
