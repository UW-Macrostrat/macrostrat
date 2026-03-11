
CREATE SCHEMA carto_new;
ALTER SCHEMA carto_new OWNER TO macrostrat_admin;
SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE TABLE carto_new.hex_index (
    map_id integer NOT NULL,
    scale text,
    hex_id integer
);
ALTER TABLE carto_new.hex_index OWNER TO macrostrat;

CREATE TABLE carto_new.pbdb_hex_index (
  collection_no integer NOT NULL,
  scale text,
  hex_id integer
);

CREATE VIEW carto_new.large AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    (polygons.geom_scale)::text AS scale
   FROM carto.polygons
  WHERE (polygons.scale = 'large'::maps.map_scale);

CREATE VIEW carto_new.lines_large AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    (lines.geom_scale)::text AS scale
   FROM carto.lines
  WHERE (lines.scale = 'large'::maps.map_scale);

CREATE VIEW carto_new.lines_medium AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    (lines.geom_scale)::text AS scale
   FROM carto.lines
  WHERE (lines.scale = 'medium'::maps.map_scale);

CREATE VIEW carto_new.lines_small AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    (lines.geom_scale)::text AS scale
   FROM carto.lines
  WHERE (lines.scale = 'small'::maps.map_scale);

CREATE VIEW carto_new.lines_tiny AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    (lines.geom_scale)::text AS scale
   FROM carto.lines
  WHERE (lines.scale = 'tiny'::maps.map_scale);

CREATE VIEW carto_new.medium AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    (polygons.geom_scale)::text AS scale
   FROM carto.polygons
  WHERE (polygons.scale = 'medium'::maps.map_scale);

CREATE VIEW carto_new.small AS
SELECT polygons.map_id,
  polygons.source_id,
  polygons.geom,
  (polygons.geom_scale)::text AS scale
FROM carto.polygons
WHERE (polygons.scale = 'small'::maps.map_scale);

CREATE VIEW carto_new.tiny AS
SELECT polygons.map_id,
  polygons.source_id,
  polygons.geom,
  (polygons.geom_scale)::text AS scale
FROM carto.polygons
WHERE (polygons.scale = 'tiny'::maps.map_scale);

CREATE INDEX hex_index_hex_id_idx ON carto_new.hex_index USING btree (hex_id);

CREATE INDEX hex_index_map_id_idx ON carto_new.hex_index USING btree (map_id);

CREATE INDEX hex_index_scale_idx ON carto_new.hex_index USING btree (scale);

CREATE INDEX pbdb_hex_index_collection_no_idx ON carto_new.pbdb_hex_index USING btree (collection_no);

CREATE INDEX pbdb_hex_index_hex_id_idx ON carto_new.pbdb_hex_index USING btree (hex_id);

CREATE INDEX pbdb_hex_index_scale_idx ON carto_new.pbdb_hex_index USING btree (scale);

GRANT SELECT ON ALL TABLES IN SCHEMA carto_new TO macrostrat;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat_admin IN SCHEMA carto_new GRANT SELECT,USAGE ON SEQUENCES  TO macrostrat;
ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat_admin IN SCHEMA carto_new GRANT SELECT ON TABLES  TO macrostrat;

