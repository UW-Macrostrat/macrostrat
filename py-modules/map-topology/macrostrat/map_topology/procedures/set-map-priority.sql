-- Associate maps with compilations

INSERT INTO map_bounds.map_priority (
  map_layer,
  map_id,
  priority
)
SELECT
  map_layer,
  s.source_id,
  new_priority + CASE WHEN s.scale = 'tiny' THEN -20000
                  WHEN s.scale = 'small' THEN -10000
                  WHEN s.scale = 'medium' THEN 0
                  WHEN s.scale = 'large' THEN 10000
                  ELSE 0 END AS priority
FROM map_bounds.map_area a
JOIN maps.sources s ON a.id = s.source_id
ON CONFLICT (map_layer, map_id)
DO UPDATE SET priority = EXCLUDED.priority;


/** Temporary: associate maps directly with layers (means maps can only be in one layer) **/
UPDATE map_bounds.map_area
SET map_layer = map_bounds.layer_id(s.scale)
FROM maps.sources s
WHERE map_bounds.map_area.id = s.source_id
  AND s.scale IS NOT NULL;

SELECT * FROM map_bounds.map_area WHERE id = 154;
