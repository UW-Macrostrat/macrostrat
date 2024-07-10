SET search_path TO map_bounds, maps, public;

DELETE FROM map_bounds.map_layer WHERE name = 'Default';
DELETE FROM map_bounds.linework_type WHERE name = 'Default';

INSERT INTO map_bounds.map_layer (id, name, description, topological) VALUES
    (1, 'map_bounds', 'Map boundary rgeom', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO map_bounds.linework_type (id, name) VALUES
    ('map_bounds', 'Map boundary')
ON CONFLICT DO NOTHING;

INSERT INTO map_bounds.map_layer_linework_type (map_layer, type)
VALUES (1, 'map_bounds');

INSERT INTO map_bounds.linework (geometry, source_id, type, map_layer)
SELECT ST_MakeValid(ST_Boundary(rgeom)), source_id, 'map_bounds', 1
  FROM maps.sources
  WHERE rgeom IS NOT NULL;
