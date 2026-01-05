SET search_path TO map_bounds, maps, public;

INSERT INTO map_bounds.map_area (source_id, geometry, area_km)
SELECT
  source_id,
  ST_Multi(rgeom),
  ST_Area(rgeom::geography) / 1e6
FROM maps.sources
WHERE rgeom IS NOT NULL
  AND is_finalized
  AND status_code = 'active'
ON CONFLICT (source_id)
DO NOTHING;
