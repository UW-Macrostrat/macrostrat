-- Associate maps with compilations

INSERT INTO map_bounds.map_priority (
  map_layer,
  map_id,
  priority
)
SELECT
  map_bounds.layer_id('tiny'),
  source_id,
  priority
FROM map_bounds.scale_priority
WHERE scale = 'tiny'
UNION ALL
SELECT
  map_bounds.layer_id('small'),
  source_id,
  priority
FROM map_bounds.scale_priority
WHERE scale IN ('tiny', 'small')
UNION ALL
SELECT
  map_bounds.layer_id('medium'),
  source_id,
  priority
FROM map_bounds.scale_priority
WHERE scale IN ('small', 'medium')
UNION ALL
SELECT
  map_bounds.layer_id('large'),
  source_id,
  priority
FROM map_bounds.scale_priority
WHERE scale IN ('medium', 'large')
ON CONFLICT (map_layer, map_id) DO NOTHING;


/** Temporary: associate maps directly with layers (means maps can only be in one layer) **/
UPDATE map_bounds.map_area
SET map_layer = map_bounds.layer_id(s.scale)
FROM maps.sources s
WHERE map_bounds.map_area.id = s.source_id
  AND s.scale IS NOT NULL;
