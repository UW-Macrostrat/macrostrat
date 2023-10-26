/* Rename lines tables and create views for backwards compatibility */

ALTER TABLE lines.tiny RENAME TO lines_tiny;
ALTER TABLE lines.small RENAME TO lines_small;
ALTER TABLE lines.medium RENAME TO lines_medium;
ALTER TABLE lines.large RENAME TO lines_large;

/** Remove indices on old tables */
ALTER TABLE lines.lines_tiny DROP CONSTRAINT IF EXISTS tiny_pkey;
ALTER TABLE lines.lines_small DROP CONSTRAINT IF EXISTS small_pkey;
ALTER TABLE lines.lines_medium DROP CONSTRAINT IF EXISTS medium_pkey;
ALTER TABLE lines.lines_large DROP CONSTRAINT IF EXISTS large_pkey;

/* Remove old validity constraints */
ALTER TABLE lines.lines_tiny DROP CONSTRAINT IF EXISTS "ST_IsValid(geom)";
ALTER TABLE lines.lines_small DROP CONSTRAINT IF EXISTS enforce_valid_geom_lines_small;
ALTER TABLE lines.lines_medium DROP CONSTRAINT IF EXISTS enforce_valid_geom_lines_medium;
ALTER TABLE lines.lines_large DROP CONSTRAINT IF EXISTS "ST_IsValid(geom)";

DROP INDEX lines.tiny_geom_idx;
DROP INDEX lines.small_geom_idx;
DROP INDEX lines.medium_geom_idx;
DROP INDEX lines.large_geom_idx;

DROP INDEX lines.tiny_line_id_idx;
DROP INDEX lines.small_line_id_idx;
DROP INDEX lines.medium_line_id_idx;
DROP INDEX lines.large_line_id_idx;

DROP INDEX lines.tiny_orig_id_idx;
DROP INDEX lines.small_orig_id_idx;
DROP INDEX lines.medium_orig_id_idx;
DROP INDEX lines.large_orig_id_idx;

DROP INDEX lines.tiny_source_id_idx;
DROP INDEX lines.small_source_id_idx;
DROP INDEX lines.medium_source_id_idx;
DROP INDEX lines.large_source_id_idx;

DROP INDEX lines.tiny_pkey;
DROP INDEX lines.small_pkey;
DROP INDEX lines.medium_pkey;
DROP INDEX lines.large_pkey;

/* Move to new schema */
ALTER TABLE lines.lines_tiny SET SCHEMA maps;
ALTER TABLE lines.lines_small SET SCHEMA maps;
ALTER TABLE lines.lines_medium SET SCHEMA maps;
ALTER TABLE lines.lines_large SET SCHEMA maps;

ALTER TABLE maps.lines_tiny ADD COLUMN scale map_scale NOT NULL DEFAULT 'tiny';
ALTER TABLE maps.lines_small ADD COLUMN scale map_scale NOT NULL DEFAULT 'small';
ALTER TABLE maps.lines_medium ADD COLUMN scale map_scale NOT NULL DEFAULT 'medium';
ALTER TABLE maps.lines_large ADD COLUMN scale map_scale NOT NULL DEFAULT 'large';

DROP VIEW IF EXISTS tile_layers.map_lines;
DROP VIEW IF EXISTS tile_layers.line_data;

ALTER TABLE maps.lines_tiny ADD CONSTRAINT lines_tiny_scale_check CHECK (scale = 'tiny');
ALTER TABLE maps.lines_small ADD CONSTRAINT lines_small_scale_check CHECK (scale = 'small');
ALTER TABLE maps.lines_medium ADD CONSTRAINT lines_medium_scale_check CHECK (scale = 'medium');
ALTER TABLE maps.lines_large ADD CONSTRAINT lines_large_scale_check CHECK (scale = 'large');

/* Harmonize types of direction column */
ALTER TABLE maps.lines_tiny ALTER COLUMN direction TYPE character varying(40);
ALTER TABLE maps.lines_small ALTER COLUMN direction TYPE character varying(40);
ALTER TABLE maps.lines_medium ALTER COLUMN direction TYPE character varying(40);

ALTER TABLE maps.lines_tiny ALTER COLUMN new_direction TYPE character varying(40);
ALTER TABLE maps.lines_small ALTER COLUMN new_direction TYPE character varying(40);
ALTER TABLE maps.lines_medium ALTER COLUMN new_direction TYPE character varying(40);


CREATE TABLE maps.lines (
    line_id integer DEFAULT nextval('line_ids'::regclass),
    orig_id integer,
    source_id integer REFERENCES maps.sources(source_id),
    name character varying(255),
    type character varying(100),
    direction character varying(40),
    descrip text,
    geom geometry(Geometry,4326) NOT NULL,
    new_type character varying(100),
    new_direction character varying(40),
    scale map_scale NOT NULL
) PARTITION BY LIST (scale);

ALTER TABLE maps.lines ATTACH PARTITION maps.lines_tiny FOR VALUES IN ('tiny');
ALTER TABLE maps.lines ATTACH PARTITION maps.lines_small FOR VALUES IN ('small');
ALTER TABLE maps.lines ATTACH PARTITION maps.lines_medium FOR VALUES IN ('medium');
ALTER TABLE maps.lines ATTACH PARTITION maps.lines_large FOR VALUES IN ('large');


/* Validity-checking functions */
CREATE OR REPLACE FUNCTION maps.lines_geom_is_valid(geom geometry) RETURNS boolean AS $$
  SELECT ST_IsValid(geom) AND ST_GeometryType(geom) IN ('ST_LineString', 'ST_MultiLineString');
$$ LANGUAGE SQL IMMUTABLE;

/* Create new constraints after adding partitions so all tables inherit them */
ALTER TABLE maps.lines ADD CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom));

/* Adjust columns for modern table layout */
ALTER TABLE maps.lines ALTER COLUMN line_id SET NOT NULL;
ALTER TABLE maps.lines RENAME COLUMN direction TO direction_legacy;
ALTER TABLE maps.lines RENAME COLUMN type TO type_legacy;
ALTER TABLE maps.lines RENAME COLUMN new_direction TO direction;
ALTER TABLE maps.lines RENAME COLUMN new_type TO type;


-- CREATE UNIQUE INDEX large_pkey ON lines.lines_large(line_id int4_ops);
-- CREATE INDEX large_geom_idx ON lines.lines_large USING GIST (geom gist_geometry_ops_2d);
-- CREATE INDEX large_line_id_idx ON lines.lines_large(line_id int4_ops);
-- CREATE INDEX large_orig_id_idx ON lines.lines_large(orig_id int4_ops);
-- CREATE INDEX large_source_id_idx ON lines.lines_large(source_id int4_ops);



/** Views maintaining v1 layout of maps tables */
CREATE OR REPLACE VIEW lines.tiny AS
SELECT
  line_id,
  orig_id,
  source_id,
  name,
  type_legacy type,
  direction_legacy direction,
  descrip,
  geom,
  type new_type,
  direction new_direction
FROM maps.lines WHERE scale = 'tiny';

CREATE OR REPLACE VIEW lines.small AS
SELECT
  line_id,
  orig_id,
  source_id,
  name,
  type_legacy type,
  direction_legacy direction,
  descrip,
  geom,
  type new_type,
  direction new_direction
FROM maps.lines WHERE scale = 'small';

CREATE OR REPLACE VIEW lines.medium AS
SELECT
  line_id,
  orig_id,
  source_id,
  name,
  type_legacy type,
  direction_legacy direction,
  descrip,
  geom,
  type new_type,
  direction new_direction
FROM maps.lines WHERE scale = 'medium';

CREATE OR REPLACE VIEW lines.large AS
SELECT
  line_id,
  orig_id,
  source_id,
  name,
  type_legacy type,
  direction_legacy direction,
  descrip,
  geom,
  type new_type,
  direction new_direction
FROM maps.lines WHERE scale = 'large';