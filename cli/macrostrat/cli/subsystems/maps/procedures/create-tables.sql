CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "postgis_topology";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS map_bounds;

-- Pick a relatively small tolerance to avoid gaps
SELECT topology.CreateTopology('map_bounds_topology', 4326, 0.0001);


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

SELECT topology.AddTopoGeometryColumn('map_bounds_topology', 'map_bounds','map_topo', 'topo','POLYGON');

CREATE INDEX IF NOT EXISTS map_bounds_map_topo_geometry_idx ON map_bounds.map_topo USING gist (geometry);

