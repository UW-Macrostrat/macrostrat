SET search_path TO map_bounds, maps, public;

DELETE FROM map_bounds.map_layer WHERE name = 'Default';
DELETE FROM map_bounds.linework_type WHERE name = 'Default';

INSERT INTO map_bounds.map_layer (id, name, description, topological) VALUES
    (1, 'map_bounds', 'Map boundary rgeom', TRUE),
    (2, 'grid', 'Grid', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO map_bounds.linework_type (id, name) VALUES
    ('map_bounds', 'Map boundary'),
    ('grid', 'Grid')
ON CONFLICT DO NOTHING;

INSERT INTO map_bounds.map_layer_linework_type (map_layer, type)
VALUES (1, 'map_bounds'),  (2, 'grid');

/**
  Create and insert a lon/lat grid for the world, to ensure faces are relatively small and
  easy to update
 */
WITH lon_range AS (
  SELECT generate_series(-180, 180, 5) AS lon
)
INSERT INTO map_bounds.linework (geometry, type, map_layer)
SELECT ST_MakeLine(ST_MakePoint(lon, -90), ST_MakePoint(lon, 90)), 'grid', 2
  FROM lon_range
ON CONFLICT DO NOTHING;

WITH lat_range AS (
  SELECT generate_series(-90, 90, 5) AS lat
)
INSERT INTO map_bounds.linework (geometry, type, map_layer)
SELECT ST_MakeLine(ST_MakePoint(-180, lat), ST_MakePoint(180, lat)), 'grid', 2
  FROM lat_range
ON CONFLICT DO NOTHING;


WITH a AS (
  SELECT
    ST_MakeValid(ST_SnapToGrid((ST_Dump(ST_Boundary(rgeom))).geom, 0.0001)) geometry,
    source_id
  FROM maps.sources
  WHERE rgeom IS NOT NULL
    AND is_finalized
)
INSERT INTO map_bounds.linework (geometry, source_id, type, map_layer)
SELECT (ST_Dump(
  ST_Segmentize(geometry, 1)
  )).geom, source_id, 'map_bounds', 1
FROM a
ON CONFLICT DO NOTHING;

-- Unnest boundaries and split by grid

