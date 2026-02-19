/** This is an idempotent migration to apply partitioning
  to Macrostrat's carto tables.
*/

-- https://www.postgresql.org/docs/current/ddl-partitioning.html

/* Apply partitions to existing maps tables */

CREATE SCHEMA IF NOT EXISTS carto;

ALTER TABLE carto_new.tiny RENAME TO polygons_tiny;
ALTER TABLE carto_new.small RENAME TO polygons_small;
ALTER TABLE carto_new.medium RENAME TO polygons_medium;
ALTER TABLE carto_new.large RENAME TO polygons_large;

DROP TABLE IF EXISTS carto.polygons_tiny;
DROP TABLE IF EXISTS carto.polygons_small;
DROP TABLE IF EXISTS carto.polygons_medium;
DROP TABLE IF EXISTS carto.polygons_large;

ALTER TABLE carto_new.polygons_tiny SET SCHEMA carto;
ALTER TABLE carto_new.polygons_small SET SCHEMA carto;
ALTER TABLE carto_new.polygons_medium SET SCHEMA carto;
ALTER TABLE carto_new.polygons_large SET SCHEMA carto;

/* Before this change, the scale column referred to an individual feature's
scale within a particular zoom level, not the scale of the zoom level itself.
We have retained this information in the `geom_scale` field so we can easily
tell which features are underzoomed */
ALTER TABLE carto.polygons_tiny ALTER COLUMN scale TYPE maps.map_scale USING scale::maps.map_scale;
ALTER TABLE carto.polygons_small ALTER COLUMN scale TYPE maps.map_scale USING scale::maps.map_scale;
ALTER TABLE carto.polygons_medium ALTER COLUMN scale TYPE maps.map_scale USING scale::maps.map_scale;
ALTER TABLE carto.polygons_large ALTER COLUMN scale TYPE maps.map_scale USING scale::maps.map_scale;
-- Rename to `geom_scale` to avoid confusion
ALTER TABLE carto.polygons_tiny RENAME COLUMN scale TO geom_scale;
ALTER TABLE carto.polygons_small RENAME COLUMN scale TO geom_scale;
ALTER TABLE carto.polygons_medium RENAME COLUMN scale TO geom_scale;
ALTER TABLE carto.polygons_large RENAME COLUMN scale TO geom_scale;

ALTER TABLE carto.polygons_tiny ALTER COLUMN geom_scale SET NOT NULL;
ALTER TABLE carto.polygons_small ALTER COLUMN geom_scale SET NOT NULL;
ALTER TABLE carto.polygons_medium ALTER COLUMN geom_scale SET NOT NULL;
ALTER TABLE carto.polygons_large ALTER COLUMN geom_scale SET NOT NULL;

/* Prepare for partitioning */
ALTER TABLE carto.polygons_tiny
  ADD COLUMN scale maps.map_scale NOT NULL DEFAULT 'tiny';
ALTER TABLE carto.polygons_small
  ADD COLUMN scale maps.map_scale NOT NULL DEFAULT 'small';
ALTER TABLE carto.polygons_medium
  ADD COLUMN scale maps.map_scale NOT NULL DEFAULT 'medium';
ALTER TABLE carto.polygons_large
  ADD COLUMN scale maps.map_scale NOT NULL DEFAULT 'large';

/* Add a not-null constraint */
ALTER TABLE carto.polygons_tiny ALTER COLUMN map_id SET NOT NULL;
ALTER TABLE carto.polygons_small ALTER COLUMN map_id SET NOT NULL;
ALTER TABLE carto.polygons_medium ALTER COLUMN map_id SET NOT NULL;
ALTER TABLE carto.polygons_large ALTER COLUMN map_id SET NOT NULL;

/* Be explicit about expected SRID */
ALTER TABLE carto.polygons_tiny ALTER COLUMN geom TYPE geometry(Geometry, 4326) USING ST_SetSRID(geom, 4326);
ALTER TABLE carto.polygons_small ALTER COLUMN geom TYPE geometry(Geometry, 4326) USING ST_SetSRID(geom, 4326);
ALTER TABLE carto.polygons_medium ALTER COLUMN geom TYPE geometry(Geometry, 4326) USING ST_SetSRID(geom, 4326);
ALTER TABLE carto.polygons_large ALTER COLUMN geom TYPE geometry(Geometry, 4326) USING ST_SetSRID(geom, 4326);

/* Add check constraints */
ALTER TABLE carto.polygons_tiny
  ADD CONSTRAINT polygons_tiny_scale_check CHECK (scale = 'tiny');
ALTER TABLE carto.polygons_small
  ADD CONSTRAINT polygons_small_scale_check CHECK (scale = 'small');
ALTER TABLE carto.polygons_medium
  ADD CONSTRAINT polygons_medium_scale_check CHECK (scale = 'medium');
ALTER TABLE carto.polygons_large
  ADD CONSTRAINT polygons_large_scale_check CHECK (scale = 'large');

ALTER TABLE carto.polygons_tiny ALTER COLUMN geom SET NOT NULL;
ALTER TABLE carto.polygons_small ALTER COLUMN geom SET NOT NULL;
ALTER TABLE carto.polygons_medium ALTER COLUMN geom SET NOT NULL;
ALTER TABLE carto.polygons_large ALTER COLUMN geom SET NOT NULL;

/* Create a new table to wrap together partitions */
CREATE TABLE carto.polygons (
  map_id integer NOT NULL,
  source_id integer REFERENCES maps.sources(source_id),
  geom geometry(Geometry, 4326) NOT NULL,
  /* This is the scale of the input feature (each level can have features from many scales) */
  geom_scale maps.map_scale NOT NULL,
  /* This is the scale of the layer */
  scale maps.map_scale NOT NULL
) PARTITION BY LIST (scale);
