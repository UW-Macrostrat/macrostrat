INSERT INTO map_bounds.map_area (id, geometry, area_km, map_layer)
SELECT
  source_id,
  ST_Multi(rgeom),
  ST_Area(rgeom::geography) / 1e6,
  map_bounds.layer_id(scale::text)
FROM maps.sources
WHERE rgeom IS NOT NULL
  AND is_finalized
  AND status_code = 'active'
ON CONFLICT (id) DO NOTHING;

-- Update maps that are already in the table to make sure that the area is set correctly
UPDATE map_bounds.map_area
SET area_km = ST_Area(geometry::geography) / 1e6
WHERE geometry IS NOT NULL AND area_km IS NULL;
