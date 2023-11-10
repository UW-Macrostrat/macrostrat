

CREATE SCHEMA IF NOT EXISTS ingestion_meta;

CREATE TABLE IF NOT EXISTS ingestion_meta.map_raster (
  source_id integer PRIMARY KEY REFERENCES maps.sources(source_id),
  url text NOT NULL,
  format text NOT NULL DEFAULT 'cog',
  bounds geometry(Polygon, 4326),
  projected boolean,
  proj_override text,
  comments text
);


CREATE TABLE IF NOT EXISTS ingestion_meta.tag (
  id integer PRIMARY KEY,
  name text NOT NULL,
  description text,
  color text
);

CREATE TABLE IF NOT EXISTS ingestion_meta.map_raster_quality (
  source_id integer REFERENCES maps.sources(source_id),
  tag_id integer REFERENCES ingestion_meta.tag(id)
);