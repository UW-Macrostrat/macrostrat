/** Associate maps with the layer matching their scale.

  `priority` is the plain within-layer value authored on `maps.sources`. It used
  to be packed together with a per-scale band (-20000/-10000/0/+10000) so that a
  single integer could order maps across layers as well as within one; that job
  now belongs to `map_priority.priority_path`, which `sync-priority-paths`
  builds from the composition DAG.
*/
INSERT INTO map_bounds.map_priority (map_layer, source_id, priority, derived)
SELECT
  a.map_layer,
  s.source_id,
  coalesce(s.new_priority, 0),
  false
FROM map_bounds.map_area a
JOIN maps.sources s ON a.source_id = s.source_id
/* A map that belongs to a compilation is placed *through* it, not beside it:
   its standing in the layer descends from the compilation's, which is exactly
   what the flattened path expresses. */
WHERE NOT EXISTS (
  SELECT 1 FROM map_bounds.map_composition mc WHERE mc.member_id = s.source_id
)
ON CONFLICT (map_layer, source_id)
DO UPDATE SET priority = EXCLUDED.priority, derived = false;

/* Retire the standalone placement of any map that has since become a member. */
DELETE FROM map_bounds.map_priority mp
WHERE NOT mp.derived
  AND EXISTS (
    SELECT 1 FROM map_bounds.map_composition mc WHERE mc.member_id = mp.source_id
  );


/** Temporary: associate maps directly with layers (means maps can only be in one layer) **/
UPDATE map_bounds.map_area
SET map_layer = map_bounds.layer_id(s.scale)
FROM maps.sources s
WHERE map_bounds.map_area.source_id = s.source_id
  AND s.scale IS NOT NULL;
