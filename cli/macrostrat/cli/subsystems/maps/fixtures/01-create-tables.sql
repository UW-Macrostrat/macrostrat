CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "postgis_topology";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS map_bounds;

-- Pick a relatively small tolerance to avoid gaps

SELECT topology.CreateTopology('map_bounds_topology', 4326, 0.0001)
WHERE NOT EXISTS (
  SELECT 1
  FROM topology.topology
  WHERE name = 'map_bounds_topology'
);


CREATE TABLE IF NOT EXISTS map_bounds.map_area (
  source_id integer PRIMARY KEY REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  geometry Geometry(MultiPolygon, 4326) NOT NULL,
  area_km double precision
);

CREATE TABLE IF NOT EXISTS map_bounds.map_topo (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_id integer REFERENCES map_bounds.map_area(source_id) ON DELETE CASCADE,
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
  densify integer DEFAULT NULL
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
    IF densify IS NOT NULL THEN
      /** Create shorter segments to improve snapping behavior */
      _geom := ST_Segmentize(_geom, ST_Length(_geom) / densify::double precision);
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
