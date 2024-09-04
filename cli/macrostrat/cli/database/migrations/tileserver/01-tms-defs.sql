CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS tile_utils;

CREATE TABLE IF NOT EXISTS tile_utils.tms_definition (
  name text PRIMARY KEY,
  bounds geometry(Polygon) NOT NULL,
  geographic_srid integer NOT NULL DEFAULT 4326 REFERENCES spatial_ref_sys(srid)
);

INSERT INTO tile_utils.tms_definition (name, bounds, geographic_srid) VALUES (
  'web_mercator',
  ST_TileEnvelope(0, 0, 0),
  4326
) ON CONFLICT DO NOTHING;

CREATE OR REPLACE FUNCTION tile_utils.default_tms()
RETURNS text AS $$ SELECT 'web_mercator'; $$
LANGUAGE SQL;
