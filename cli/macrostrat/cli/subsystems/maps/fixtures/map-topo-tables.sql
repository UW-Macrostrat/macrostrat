CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "postgis_topology";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

SELECT topology.CreateTopology(:topo_name, :srid, :tolerance);

CREATE SCHEMA IF NOT EXISTS map_bounds;

CREATE TABLE IF NOT EXISTS map_bounds.map_area (
  source_id integer PRIMARY KEY REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  geometry Geometry(MultiPolygon, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS map_bounds.map_topo (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_id integer REFERENCES map_bounds.map_area(source_id) ON DELETE CASCADE,
  geometry Geometry(MultiPolygon, 4326) NOT NULL,
  geometry_hash uuid,
  topology_error text
);

SELECT topology.AddTopoGeometryColumn(:topo_name, 'map_bounds','map_topo', 'topo','POLYGON');

CREATE INDEX IF NOT EXISTS map_bounds_map_topo_geometry_idx ON map_bounds.map_topo USING gist (geometry);

