/** This file runs a stripped-down version of the "partition-carto" migration,
  in order to evolve the test dataset to a newer version.
  */


-- Insert a missing source
INSERT INTO maps.sources (source_id, name)
VALUES (133, 'State Geologic Map Compilation');


CREATE TYPE map_scale AS ENUM ('tiny', 'small', 'medium', 'large');

CREATE SCHEMA carto;


/* Create a new table to wrap together partitions */
CREATE TABLE carto.polygons (
  map_id integer NOT NULL,
  source_id integer REFERENCES maps.sources(source_id),
  geom geometry(Geometry, 4326) NOT NULL,
  /* This is the scale of the input feature (each level can have features from many scales) */
  geom_scale map_scale NOT NULL,
  /* This is the scale of the layer */
  scale map_scale NOT NULL
);

/* Remove the old tables instead of partitioning. This is simpler than the
  actual migration, but it should have the same result.
*/

-- Polygons

INSERT INTO carto.polygons (map_id, source_id, geom, geom_scale, scale)
SELECT map_id, source_id, geom, scale::map_scale, 'tiny'
FROM carto_new.tiny;

INSERT INTO carto.polygons (map_id, source_id, geom, geom_scale, scale)
SELECT map_id, source_id, geom, scale::map_scale, 'small'
FROM carto_new.small;

INSERT INTO carto.polygons (map_id, source_id, geom, geom_scale, scale)
SELECT map_id, source_id, geom, scale::map_scale, 'medium'
FROM carto_new.medium;

INSERT INTO carto.polygons (map_id, source_id, geom, geom_scale, scale)
SELECT map_id, source_id, geom, scale::map_scale, 'large'
FROM carto_new.large;

-- Lines

CREATE TABLE carto.lines (
  line_id integer PRIMARY KEY,
  source_id integer REFERENCES maps.sources(source_id),
  geom geometry(Geometry, 4326) NOT NULL,
  geom_scale map_scale NOT NULL,
  scale map_scale NOT NULL
);

INSERT INTO carto.lines (line_id, source_id, geom, geom_scale, scale)
SELECT line_id, source_id, geom, scale::map_scale, 'tiny'
FROM carto_new.lines_tiny;

INSERT INTO carto.lines (line_id, source_id, geom, geom_scale, scale)
SELECT line_id, source_id, geom, scale::map_scale, 'small'
FROM carto_new.lines_small;

INSERT INTO carto.lines (line_id, source_id, geom, geom_scale, scale)
SELECT line_id, source_id, geom, scale::map_scale, 'medium'
FROM carto_new.lines_medium;

INSERT INTO carto.lines (line_id, source_id, geom, geom_scale, scale)
SELECT line_id, source_id, geom, scale::map_scale, 'large'
FROM carto_new.lines_large;

DROP SCHEMA carto_new CASCADE;

/** Create some views for line data (we should have gotten this data) */
CREATE TABLE maps.lines (
    line_id integer PRIMARY KEY,
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
);

/** Insert line data */
INSERT INTO maps.lines (line_id, source_id, geom, scale)
SELECT line_id, source_id, geom, scale
FROM carto.lines;
