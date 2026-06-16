INSERT INTO map_bounds.map_area (id, geometry, area_km, map_layer)
SELECT
  source_id,
  ST_Multi(rgeom),
  ST_Area(rgeom::geography) / 1e6,
  map_bounds.layer_id(scale::text || '-large')
FROM maps.sources
WHERE rgeom IS NOT NULL
  AND is_finalized
  AND status_code = 'active'
ON CONFLICT (id) DO NOTHING;
