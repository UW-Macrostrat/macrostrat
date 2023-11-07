ALTER TABLE carto_new.lines_tiny SET SCHEMA carto;
ALTER TABLE carto_new.lines_small SET SCHEMA carto;
ALTER TABLE carto_new.lines_medium SET SCHEMA carto;
ALTER TABLE carto_new.lines_large SET SCHEMA carto;

ALTER TABLE carto.lines_tiny ALTER COLUMN scale TYPE map_scale USING scale::map_scale;
ALTER TABLE carto.lines_small ALTER COLUMN scale TYPE map_scale USING scale::map_scale;
ALTER TABLE carto.lines_medium ALTER COLUMN scale TYPE map_scale USING scale::map_scale;
ALTER TABLE carto.lines_large ALTER COLUMN scale TYPE map_scale USING scale::map_scale;

ALTER TABLE carto.lines_tiny RENAME COLUMN scale TO geom_scale;
ALTER TABLE carto.lines_small RENAME COLUMN scale TO geom_scale;
ALTER TABLE carto.lines_medium RENAME COLUMN scale TO geom_scale;
ALTER TABLE carto.lines_large RENAME COLUMN scale TO geom_scale;

ALTER TABLE carto.lines_tiny ALTER COLUMN geom_scale SET NOT NULL;
ALTER TABLE carto.lines_small ALTER COLUMN geom_scale SET NOT NULL;
ALTER TABLE carto.lines_medium ALTER COLUMN geom_scale SET NOT NULL;
ALTER TABLE carto.lines_large ALTER COLUMN geom_scale SET NOT NULL;

ALTER TABLE carto.lines_tiny
  ADD COLUMN scale map_scale NOT NULL DEFAULT 'tiny';
ALTER TABLE carto.lines_small
  ADD COLUMN scale map_scale NOT NULL DEFAULT 'small';
ALTER TABLE carto.lines_medium
  ADD COLUMN scale map_scale NOT NULL DEFAULT 'medium';
ALTER TABLE carto.lines_large
  ADD COLUMN scale map_scale NOT NULL DEFAULT 'large';

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
  geom_scale map_scale NOT NULL,
  scale map_scale NOT NULL
) PARTITION BY LIST (scale);

ALTER TABLE carto.lines ATTACH PARTITION carto.lines_tiny FOR VALUES IN ('tiny');
ALTER TABLE carto.lines ATTACH PARTITION carto.lines_small FOR VALUES IN ('small');
ALTER TABLE carto.lines ATTACH PARTITION carto.lines_medium FOR VALUES IN ('medium');
ALTER TABLE carto.lines ATTACH PARTITION carto.lines_large FOR VALUES IN ('large');

-- Drop extra views that get created by the above
DROP VIEW IF EXISTS carto_new.lines_tiny;
DROP VIEW IF EXISTS carto_new.lines_small;
DROP VIEW IF EXISTS carto_new.lines_medium;
DROP VIEW IF EXISTS carto_new.lines_large;