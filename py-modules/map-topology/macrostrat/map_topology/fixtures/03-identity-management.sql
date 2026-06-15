ALTER TABLE map_bounds_topology.map_face
  ADD COLUMN source_id integer REFERENCES maps.sources(source_id);
ALTER TABLE map_bounds_topology.face_identity
  ADD COLUMN source_id integer REFERENCES maps.sources(source_id);

/*
Get the map face that defines a polygon for a specific topology
*/
CREATE OR REPLACE FUNCTION map_bounds_topology.identity_for_area(
  geom geometry,
  _map_layer integer
)
  RETURNS integer AS $$
  -- Get maps that overlap the area
  SELECT id INTO result
  FROM map_bounds.map_area ma
  JOIN map_bounds.map_compilation mc
    ON mc.source_id = ma.id
   AND mc.map_layer = _map_layer
  WHERE ST_Intersects(geom, ma.geometry)
  ORDER BY priority
  LIMIT 1;
$$ LANGUAGE sql;


CREATE OR REPLACE FUNCTION map_bounds_topology.identity_for_face(face_id integer, map_layer integer)
  RETURNS integer AS $$
SELECT
  source_id
FROM map_bounds_topology.relation r
JOIN map_bounds_topology.map_face f
  ON (f.topo).id = r.topogeo_id
WHERE element_id = $1
  AND element_type = 3
  AND r.layer_id = map_bounds_topology.__map_face_layer_id()
  AND f.map_layer = $2;
$$ LANGUAGE SQL IMMUTABLE;
