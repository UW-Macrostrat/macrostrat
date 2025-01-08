SET search_path TO map_bounds, maps, public;

INSERT INTO map_bounds.map_area (source_id, geometry, area_km)
SELECT
  source_id,
  rgeom,
  ST_Area(rgeom::geography) / 1e6
FROM maps.sources
WHERE rgeom IS NOT NULL
  AND is_finalized
ON CONFLICT (source_id)
DO NOTHING;

