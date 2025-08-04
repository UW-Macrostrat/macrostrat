DROP TABLE IF EXISTS carto.lines_tiny;
DROP TABLE IF EXISTS carto.lines_small;
DROP TABLE IF EXISTS carto.lines_medium;
DROP TABLE IF EXISTS carto.lines_large;

ALTER TABLE carto_new.lines_tiny SET SCHEMA carto;
ALTER TABLE carto_new.lines_small SET SCHEMA carto;
ALTER TABLE carto_new.lines_medium SET SCHEMA carto;
ALTER TABLE carto_new.lines_large SET SCHEMA carto;

ALTER TABLE carto.lines_tiny ALTER COLUMN scale TYPE maps.map_scale USING scale::maps.map_scale;
ALTER TABLE carto.lines_small ALTER COLUMN scale TYPE maps.map_scale USING scale::maps.map_scale;
ALTER TABLE carto.lines_medium ALTER COLUMN scale TYPE maps.map_scale USING scale::maps.map_scale;
ALTER TABLE carto.lines_large ALTER COLUMN scale TYPE maps.map_scale USING scale::maps.map_scale;

ALTER TABLE carto.lines_tiny RENAME COLUMN scale TO geom_scale;
ALTER TABLE carto.lines_small RENAME COLUMN scale TO geom_scale;
ALTER TABLE carto.lines_medium RENAME COLUMN scale TO geom_scale;
ALTER TABLE carto.lines_large RENAME COLUMN scale TO geom_scale;

ALTER TABLE carto.lines_tiny ALTER COLUMN geom_scale SET NOT NULL;
ALTER TABLE carto.lines_small ALTER COLUMN geom_scale SET NOT NULL;
ALTER TABLE carto.lines_medium ALTER COLUMN geom_scale SET NOT NULL;
ALTER TABLE carto.lines_large ALTER COLUMN geom_scale SET NOT NULL;

ALTER TABLE carto.lines_tiny
  ADD COLUMN scale maps.map_scale NOT NULL DEFAULT 'tiny';
ALTER TABLE carto.lines_small
  ADD COLUMN scale maps.map_scale NOT NULL DEFAULT 'small';
ALTER TABLE carto.lines_medium
  ADD COLUMN scale maps.map_scale NOT NULL DEFAULT 'medium';
ALTER TABLE carto.lines_large
  ADD COLUMN scale maps.map_scale NOT NULL DEFAULT 'large';

ALTER TABLE carto.lines_tiny ALTER COLUMN line_id SET NOT NULL;
ALTER TABLE carto.lines_small ALTER COLUMN line_id SET NOT NULL;
ALTER TABLE carto.lines_medium ALTER COLUMN line_id SET NOT NULL;
ALTER TABLE carto.lines_large ALTER COLUMN line_id SET NOT NULL;

ALTER TABLE carto.lines_tiny ALTER COLUMN geom TYPE geometry(Geometry, 4326) USING ST_SetSRID(geom, 4326);
ALTER TABLE carto.lines_small ALTER COLUMN geom TYPE geometry(Geometry, 4326) USING ST_SetSRID(geom, 4326);
ALTER TABLE carto.lines_medium ALTER COLUMN geom TYPE geometry(Geometry, 4326) USING ST_SetSRID(geom, 4326);
ALTER TABLE carto.lines_large ALTER COLUMN geom TYPE geometry(Geometry, 4326) USING ST_SetSRID(geom, 4326);

ALTER TABLE carto.lines_tiny ALTER COLUMN geom SET NOT NULL;
ALTER TABLE carto.lines_small ALTER COLUMN geom SET NOT NULL;
ALTER TABLE carto.lines_medium ALTER COLUMN geom SET NOT NULL;
ALTER TABLE carto.lines_large ALTER COLUMN geom SET NOT NULL;

ALTER TABLE carto.lines_tiny
  ADD CONSTRAINT lines_tiny_scale_check CHECK (scale = 'tiny');
ALTER TABLE carto.lines_small
  ADD CONSTRAINT lines_small_scale_check CHECK (scale = 'small');
ALTER TABLE carto.lines_medium
  ADD CONSTRAINT lines_medium_scale_check CHECK (scale = 'medium');
ALTER TABLE carto.lines_large
  ADD CONSTRAINT lines_large_scale_check CHECK (scale = 'large');

CREATE TABLE carto.lines (
  line_id integer NOT NULL,
  source_id integer REFERENCES maps.sources(source_id),
  geom geometry(Geometry, 4326) NOT NULL,
  geom_scale maps.map_scale NOT NULL,
  scale maps.map_scale NOT NULL
) PARTITION BY LIST (scale);

ALTER TABLE carto.lines ATTACH PARTITION carto.lines_tiny FOR VALUES IN ('tiny');
ALTER TABLE carto.lines ATTACH PARTITION carto.lines_small FOR VALUES IN ('small');
ALTER TABLE carto.lines ATTACH PARTITION carto.lines_medium FOR VALUES IN ('medium');
ALTER TABLE carto.lines ATTACH PARTITION carto.lines_large FOR VALUES IN ('large');

/* Create views mimicking the old tables */
CREATE OR REPLACE VIEW carto_new.lines_tiny
AS SELECT line_id, source_id, geom, geom_scale::text AS scale
FROM carto.lines WHERE scale = 'tiny';

CREATE OR REPLACE VIEW carto_new.lines_small
AS SELECT line_id, source_id, geom, geom_scale::text AS scale
FROM carto.lines WHERE scale = 'small';

CREATE OR REPLACE VIEW carto_new.lines_medium
AS SELECT line_id, source_id, geom, geom_scale::text AS scale
FROM carto.lines WHERE scale = 'medium';

CREATE OR REPLACE VIEW carto_new.lines_large
AS SELECT line_id, source_id, geom, geom_scale::text AS scale
FROM carto.lines WHERE scale = 'large';
