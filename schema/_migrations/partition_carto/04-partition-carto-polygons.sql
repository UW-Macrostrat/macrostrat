/* Add the existing tables as partitions */
ALTER TABLE carto.polygons ATTACH PARTITION carto.polygons_tiny FOR VALUES IN ('tiny');
ALTER TABLE carto.polygons ATTACH PARTITION carto.polygons_small FOR VALUES IN ('small');
ALTER TABLE carto.polygons ATTACH PARTITION carto.polygons_medium FOR VALUES IN ('medium');
ALTER TABLE carto.polygons ATTACH PARTITION carto.polygons_large FOR VALUES IN ('large');

/* Legacy tables as views */
CREATE OR REPLACE VIEW carto_new.tiny
AS SELECT map_id, source_id, geom, geom_scale::text AS scale
FROM carto.polygons WHERE scale = 'tiny';

CREATE OR REPLACE VIEW carto_new.small
AS SELECT map_id, source_id, geom, geom_scale::text AS scale
FROM carto.polygons WHERE scale = 'small';

CREATE OR REPLACE VIEW carto_new.medium
AS SELECT map_id, source_id, geom, geom_scale::text AS scale
FROM carto.polygons WHERE scale = 'medium';

CREATE OR REPLACE VIEW carto_new.large
AS SELECT map_id, source_id, geom, geom_scale::text AS scale
FROM carto.polygons WHERE scale = 'large';

CREATE INDEX IF NOT EXISTS carto_polygons_geom_gist ON carto.polygons USING gist (geom);

-- Drop extra views that get created during the process
DROP VIEW IF EXISTS carto_new.polygons_tiny;
DROP VIEW IF EXISTS carto_new.polygons_small;
DROP VIEW IF EXISTS carto_new.polygons_medium;
DROP VIEW IF EXISTS carto_new.polygons_large;

-- Add a primary key constraint.
/** Once we have reduced duplicate geometries, we can add a unique constraint */
ALTER TABLE carto.polygons DROP CONSTRAINT polygons_pkey;
ALTER TABLE carto.polygons ADD CONSTRAINT polygons_pkey PRIMARY KEY (map_id, scale);
-- We have to also create a unique constraint in order to use this for foriegn keys, annoyingly
ALTER TABLE carto.polygons ADD CONSTRAINT polygons_unique UNIQUE (map_id, scale);
