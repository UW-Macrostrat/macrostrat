-- Associate maps with compilations

INSERT INTO map_bounds.map_compilation (
  map_layer,
  source_id,
  priority
)
SELECT
  map_bounds.layer_id('carto-tiny'),
  source_id,
  priority
FROM map_bounds.scale_priority
WHERE scale = 'tiny'
UNION ALL
SELECT
  map_bounds.layer_id('carto-small'),
  source_id,
  priority
FROM map_bounds.scale_priority
WHERE scale IN ('tiny', 'small')
UNION ALL
SELECT
  map_bounds.layer_id('carto-medium'),
  source_id,
  priority
FROM map_bounds.scale_priority
WHERE scale IN ('small', 'medium')
UNION ALL
SELECT
  map_bounds.layer_id('carto-large'),
  source_id,
  priority
FROM map_bounds.scale_priority
WHERE scale IN ('medium', 'large')
ON CONFLICT (map_layer, source_id) DO NOTHING;
