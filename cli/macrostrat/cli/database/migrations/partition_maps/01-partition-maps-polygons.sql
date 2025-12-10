-- Move the ID sequence to the maps schema
ALTER SEQUENCE map_ids SET SCHEMA maps;

/** Rename maps tables and create views for backwards compatibility */
CREATE TYPE maps.map_scale AS ENUM ('tiny', 'small', 'medium', 'large');

ALTER TABLE maps.tiny RENAME TO polygons_tiny;
ALTER TABLE maps.small RENAME TO polygons_small;
ALTER TABLE maps.medium RENAME TO polygons_medium;
ALTER TABLE maps.large RENAME TO polygons_large;

/* Legacy views */
CREATE VIEW maps.tiny AS SELECT * FROM maps.polygons_tiny;
CREATE VIEW maps.small AS SELECT * FROM maps.polygons_small;
CREATE VIEW maps.medium AS SELECT * FROM maps.polygons_medium;
CREATE VIEW maps.large AS SELECT * FROM maps.polygons_large;

ALTER TABLE maps.polygons_tiny ADD COLUMN scale maps.map_scale NOT NULL DEFAULT 'tiny';
ALTER TABLE maps.polygons_small ADD COLUMN scale maps.map_scale NOT NULL DEFAULT 'small';
ALTER TABLE maps.polygons_medium ADD COLUMN scale maps.map_scale NOT NULL DEFAULT 'medium';
ALTER TABLE maps.polygons_large ADD COLUMN scale maps.map_scale NOT NULL DEFAULT 'large';

ALTER TABLE maps.polygons_tiny ADD CONSTRAINT polygons_tiny_scale_check CHECK (scale = 'tiny');
ALTER TABLE maps.polygons_small ADD CONSTRAINT polygons_small_scale_check CHECK (scale = 'small');
ALTER TABLE maps.polygons_medium ADD CONSTRAINT polygons_medium_scale_check CHECK (scale = 'medium');
ALTER TABLE maps.polygons_large ADD CONSTRAINT polygons_large_scale_check CHECK (scale = 'large');

CREATE OR REPLACE FUNCTION maps.polygons_geom_is_valid(geom geometry) RETURNS boolean AS $$
  SELECT ST_IsValid(geom) AND ST_GeometryType(geom) IN ('ST_Polygon', 'ST_MultiPolygon');
$$ LANGUAGE SQL IMMUTABLE;

/** Create a new table to wrap together partitions */
CREATE TABLE maps.polygons (
  /* Due to PostgreSQL internal limitations, uniqueness of this map_id
  can be enforced only within each partition. */
  map_id integer DEFAULT nextval('maps.map_ids'::regclass) NOT NULL,
  source_id integer REFERENCES maps.sources(source_id) NOT NULL,
  scale maps.map_scale NOT NULL,
  orig_id text,
  name text,
  strat_name text,
  age character varying(255),
  lith text,
  descrip text,
  comments text,
  t_interval integer,
  b_interval integer,
  geom geometry(Geometry,4326) NOT NULL,
  CONSTRAINT maps_polygons_pkey PRIMARY KEY (map_id, scale),
  CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom))
) PARTITION BY LIST (scale);

/** Remove old primary key constraints */
ALTER TABLE maps.polygons_tiny DROP CONSTRAINT IF EXISTS tiny_pkey;
ALTER TABLE maps.polygons_small DROP CONSTRAINT IF EXISTS small_pkey;
ALTER TABLE maps.polygons_medium DROP CONSTRAINT IF EXISTS medium_pkey;
ALTER TABLE maps.polygons_large DROP CONSTRAINT IF EXISTS large_pkey;

/** Share the primary key constraint across partitions */
ALTER TABLE maps.polygons_tiny ADD CONSTRAINT maps_polygons_tiny_pkey PRIMARY KEY (map_id, scale);
ALTER TABLE maps.polygons_small ADD CONSTRAINT maps_polygons_small_pkey PRIMARY KEY (map_id, scale);
ALTER TABLE maps.polygons_medium ADD CONSTRAINT maps_polygons_medium_pkey PRIMARY KEY (map_id, scale);
ALTER TABLE maps.polygons_large ADD CONSTRAINT maps_polygons_large_pkey PRIMARY KEY (map_id, scale);

/** Enforce geometry validity */
ALTER TABLE maps.polygons_tiny ADD CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom));
ALTER TABLE maps.polygons_small ADD CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom));
ALTER TABLE maps.polygons_medium ADD CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom));
ALTER TABLE maps.polygons_large ADD CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom));

ALTER TABLE maps.polygons_tiny ALTER COLUMN source_id SET NOT NULL;
ALTER TABLE maps.polygons_small ALTER COLUMN source_id SET NOT NULL;
ALTER TABLE maps.polygons_medium ALTER COLUMN source_id SET NOT NULL;
ALTER TABLE maps.polygons_large ALTER COLUMN source_id SET NOT NULL;

/* Add foreign key constraints */
ALTER TABLE maps.polygons_tiny ADD CONSTRAINT maps_polygons_tiny_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);
ALTER TABLE maps.polygons_small ADD CONSTRAINT maps_polygons_small_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);
ALTER TABLE maps.polygons_medium ADD CONSTRAINT maps_polygons_medium_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);
ALTER TABLE maps.polygons_large ADD CONSTRAINT maps_polygons_large_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);

/* Remove old constraints */
ALTER TABLE maps.polygons_tiny DROP CONSTRAINT IF EXISTS enforce_geom_type_tiny;
ALTER TABLE maps.polygons_small DROP CONSTRAINT IF EXISTS enforce_geom_type_small;
ALTER TABLE maps.polygons_medium DROP CONSTRAINT IF EXISTS enforce_geom_type_medium;
ALTER TABLE maps.polygons_large DROP CONSTRAINT IF EXISTS enforce_geom_type_large;

ALTER TABLE maps.polygons_tiny DROP CONSTRAINT IF EXISTS enforce_valid_geom_tiny;
ALTER TABLE maps.polygons_small DROP CONSTRAINT IF EXISTS enforce_valid_geom_small;
ALTER TABLE maps.polygons_tiny DROP CONSTRAINT IF EXISTS enforce_valid_geom_medium;
ALTER TABLE maps.polygons_small DROP CONSTRAINT IF EXISTS enforce_valid_geom_large;

/** Add the existing tables as partitions */
ALTER TABLE maps.polygons ATTACH PARTITION maps.polygons_tiny FOR VALUES IN ('tiny');
ALTER TABLE maps.polygons ATTACH PARTITION maps.polygons_small FOR VALUES IN ('small');
ALTER TABLE maps.polygons ATTACH PARTITION maps.polygons_medium FOR VALUES IN ('medium');
ALTER TABLE maps.polygons ATTACH PARTITION maps.polygons_large FOR VALUES IN ('large');

/** Add indexes */
CREATE INDEX polygons_b_interval_idx ON maps.polygons(b_interval);
CREATE INDEX polygons_geom_idx ON maps.polygons USING GIST (geom);
CREATE INDEX polygons_name_idx ON maps.polygons(name);
CREATE INDEX polygons_orig_id_idx ON maps.polygons(orig_id);
CREATE INDEX polygons_source_id_idx ON maps.polygons(source_id);
CREATE INDEX polygons_t_interval_idx ON maps.polygons(t_interval);

