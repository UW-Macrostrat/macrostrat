
CREATE TABLE IF NOT EXISTS map_bounds.boundary (
  source_id integer PRIMARY KEY REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  geometry Geometry(MultiPolygon, 4326) NOT NULL
);


ALTER TABLE map_bounds.linework
  ADD COLUMN IF NOT EXISTS source_id integer
    REFERENCES maps.sources(source_id)
      ON DELETE CASCADE;

/** Disable triggers (there may be a better way to do this) */
CREATE OR REPLACE FUNCTION map_bounds.triggers_enabled() RETURNS boolean AS $$
  SELECT false;
$$ LANGUAGE sql;
