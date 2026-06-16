CREATE SCHEMA IF NOT EXISTS map_bounds;

-- Pick a relatively small tolerance to avoid gaps

ALTER TABLE map_bounds.map_layer ADD COLUMN IF NOT EXISTS slug text UNIQUE;
ALTER TABLE map_bounds.map_layer ADD COLUMN IF NOT EXISTS min_zoom integer;
ALTER TABLE map_bounds.map_layer ADD COLUMN IF NOT EXISTS max_zoom integer;
-- Approximate bounds for the layer
ALTER TABLE map_bounds.map_layer ADD COLUMN IF NOT EXISTS bounds Geometry(MultiPolygon, 4326);

INSERT INTO map_bounds.map_layer (slug, name, min_zoom, max_zoom, bounds, topological)
VALUES ('carto-tiny', 'Carto tiny', 0, 4, ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true),
  ('carto-small', 'Carto small', 4, 8, ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true),
  ('carto-medium', 'Carto medium', 0, 12, ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true),
  ('carto-large', 'Carto large', 0, 18, ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true)
ON CONFLICT (slug) DO NOTHING;


SELECT topology.CreateTopology('map_bounds_topology', 4326, 0.0001)
WHERE NOT EXISTS (
  SELECT 1
  FROM topology.topology
  WHERE name = 'map_bounds_topology'
);

/** The area of full maps in the topology */
CREATE TABLE IF NOT EXISTS map_bounds.map_area (
  id integer PRIMARY KEY REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  geometry Geometry(MultiPolygon, 4326) NOT NULL,
  geometry_hash uuid,
  topology_error text,
  map_layer integer REFERENCES map_bounds.map_layer(id),
  area_km double precision
);

/** Create a topogeometry column for the area of full maps. */
SELECT topology.AddTopoGeometryColumn('map_bounds_topology', 'map_bounds','map_area', 'topo','POLYGON')
WHERE NOT EXISTS (
  SELECT 1
  FROM topology.topology
  JOIN topology.layer
  ON topology.topology.id = topology.layer.topology_id
  WHERE topology.name = 'map_bounds_topology'
    AND topology.layer.schema_name = 'map_bounds'
    AND topology.layer.table_name = 'map_area'
    AND topology.layer.feature_column = 'topo'
);

/**
  Store polygonal parts of a map area. This exists to allow for more incremental
  maintenance for map faces
*/
CREATE TABLE IF NOT EXISTS map_bounds.map_topo (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  map_id integer REFERENCES map_bounds.map_area(id) ON DELETE CASCADE,
  geometry Geometry(MultiPolygon, 4326) NOT NULL,
  -- For tracking whether the geometry and topology are in sync
  geometry_hash uuid,
  topology_error text
);


SELECT topology.AddTopoGeometryColumn('map_bounds_topology', 'map_bounds','map_topo', 'topo','POLYGON')
WHERE NOT EXISTS (
  SELECT 1
  FROM topology.topology
  JOIN topology.layer
  ON topology.topology.id = topology.layer.topology_id
  WHERE topology.name = 'map_bounds_topology'
    AND topology.layer.schema_name = 'map_bounds'
    AND topology.layer.table_name = 'map_topo'
    AND topology.layer.feature_column = 'topo'
);

CREATE INDEX IF NOT EXISTS map_bounds_map_topo_geometry_idx ON map_bounds.map_topo USING gist (geometry);

/** Function to update topogeometry for a row, updating the geometry hash and setting/clearing
  topology errors as appropriate.
 */
CREATE OR REPLACE FUNCTION map_bounds.update_topogeom(
  map_topo map_bounds.map_topo,
  tolerance double precision DEFAULT 0.0001,
  densify integer DEFAULT 1
) RETURNS text AS
$$
  DECLARE
    _layer_id integer;
    _hash uuid;
    _err_text text;
    _geom geometry;
  BEGIN
    _hash := md5(ST_AsBinary(map_topo.geometry))::uuid;

    -- Get the layer identifier to update
    SELECT layer_id INTO _layer_id
    FROM topology.layer
    WHERE schema_name='map_bounds'
      AND table_name='map_topo'
      AND feature_column='topo';

    _geom := map_topo.geometry;
    IF densify > 1 THEN
      /** Create shorter segments to improve snapping behavior */
      _geom := ST_Segmentize(_geom, ST_Length(ST_Boundary(_geom)) / densify::double precision);
    END IF;

    IF (_hash = map_topo.geometry_hash) THEN
      -- We already have a valid topogeometry representation
      RETURN null;
    END IF;
    -- Set topogeometry
    UPDATE map_bounds.map_topo l
    SET
      topo = topology.toTopoGeom(
        map_topo.geometry,
        'map_bounds_topology',
        _layer_id,
        tolerance
             ),
      geometry_hash = _hash,
      topology_error = null
    WHERE l.id = map_topo.id;
    RETURN NULL;
  EXCEPTION WHEN others THEN
    _err_text := SQLSTATE || ': ' || SQLERRM;
    -- Set the error
    UPDATE map_bounds.map_topo l
    SET
      topology_error = _err_text
    WHERE l.id = map_topo.id;
    RETURN _err_text;
  END;
$$
LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION map_bounds_topology.get_topological_map_layer(_line map_bounds.map_area)
  RETURNS integer AS $$
SELECT ml.id
FROM map_bounds.map_layer ml
WHERE ml.id = $1.map_layer
  AND ml.composited_from IS NULL
  AND ml.topological;
$$ LANGUAGE SQL IMMUTABLE;
