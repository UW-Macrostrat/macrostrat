
CREATE TABLE IF NOT EXISTS map_bounds.boundary (
  source_id integer PRIMARY KEY REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  geometry Geometry(MultiPolygon, 4326) NOT NULL
);


ALTER TABLE map_bounds.linework
  ADD COLUMN IF NOT EXISTS source_id integer NOT NULL
    REFERENCES maps.sources(source_id)
      ON DELETE CASCADE;
