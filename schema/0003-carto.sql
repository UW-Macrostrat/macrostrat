

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

CREATE SCHEMA carto;
ALTER SCHEMA carto OWNER TO macrostrat;
SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE TABLE carto.flat_large (
    map_id integer,
    geom public.geometry
);
ALTER TABLE carto.flat_large OWNER TO macrostrat_admin;

CREATE TABLE carto.flat_medium (
    map_id integer,
    geom public.geometry
);
ALTER TABLE carto.flat_medium OWNER TO macrostrat_admin;

CREATE TABLE carto.large (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age text,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int text,
    best_age_top numeric,
    b_int_id integer,
    b_int text,
    best_age_bottom numeric,
    color text,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);
ALTER TABLE carto.large OWNER TO macrostrat_admin;

CREATE TABLE carto.lines (
    line_id integer NOT NULL,
    source_id integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    geom_scale maps.map_scale NOT NULL,
    scale maps.map_scale NOT NULL
)
PARTITION BY LIST (scale);
ALTER TABLE carto.lines OWNER TO macrostrat;

CREATE TABLE carto.lines_large (
    line_id integer NOT NULL,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'large'::maps.map_scale NOT NULL,
    CONSTRAINT lines_large_scale_check CHECK ((scale = 'large'::maps.map_scale))
);
ALTER TABLE carto.lines_large OWNER TO macrostrat;

CREATE TABLE carto.lines_medium (
    line_id integer NOT NULL,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'medium'::maps.map_scale NOT NULL,
    CONSTRAINT lines_medium_scale_check CHECK ((scale = 'medium'::maps.map_scale))
);
ALTER TABLE carto.lines_medium OWNER TO macrostrat;

CREATE TABLE carto.lines_small (
    line_id integer NOT NULL,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'small'::maps.map_scale NOT NULL,
    CONSTRAINT lines_small_scale_check CHECK ((scale = 'small'::maps.map_scale))
);
ALTER TABLE carto.lines_small OWNER TO macrostrat;

CREATE TABLE carto.lines_tiny (
    line_id integer NOT NULL,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'tiny'::maps.map_scale NOT NULL,
    CONSTRAINT lines_tiny_scale_check CHECK ((scale = 'tiny'::maps.map_scale))
);
ALTER TABLE carto.lines_tiny OWNER TO macrostrat;

CREATE TABLE carto.medium (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age text,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int text,
    best_age_top numeric,
    b_int_id integer,
    b_int text,
    best_age_bottom numeric,
    color text,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);
ALTER TABLE carto.medium OWNER TO macrostrat_admin;

CREATE TABLE carto.polygons (
    map_id integer NOT NULL,
    source_id integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    geom_scale maps.map_scale NOT NULL,
    scale maps.map_scale NOT NULL
)
PARTITION BY LIST (scale);
ALTER TABLE carto.polygons OWNER TO macrostrat;

CREATE TABLE carto.polygons_large (
    map_id integer NOT NULL,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'large'::maps.map_scale NOT NULL,
    CONSTRAINT polygons_large_scale_check CHECK ((scale = 'large'::maps.map_scale))
);
ALTER TABLE carto.polygons_large OWNER TO macrostrat;

CREATE TABLE carto.polygons_medium (
    map_id integer NOT NULL,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'medium'::maps.map_scale NOT NULL,
    CONSTRAINT polygons_medium_scale_check CHECK ((scale = 'medium'::maps.map_scale))
);
ALTER TABLE carto.polygons_medium OWNER TO macrostrat;

CREATE TABLE carto.polygons_small (
    map_id integer NOT NULL,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'small'::maps.map_scale NOT NULL,
    CONSTRAINT polygons_small_scale_check CHECK ((scale = 'small'::maps.map_scale))
);
ALTER TABLE carto.polygons_small OWNER TO macrostrat;

CREATE TABLE carto.polygons_tiny (
    map_id integer NOT NULL,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'tiny'::maps.map_scale NOT NULL,
    CONSTRAINT polygons_tiny_scale_check CHECK ((scale = 'tiny'::maps.map_scale))
);
ALTER TABLE carto.polygons_tiny OWNER TO macrostrat;

CREATE TABLE carto.small (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age text,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int text,
    best_age_top numeric,
    b_int_id integer,
    b_int text,
    best_age_bottom numeric,
    color text,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);
ALTER TABLE carto.small OWNER TO macrostrat_admin;

CREATE TABLE carto.tiny (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age character varying,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int character varying(200),
    best_age_top numeric,
    b_int_id integer,
    b_int character varying(200),
    best_age_bottom numeric,
    color character varying(20),
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);
ALTER TABLE carto.tiny OWNER TO macrostrat_admin;

ALTER TABLE ONLY carto.lines ATTACH PARTITION carto.lines_large FOR VALUES IN ('large');

ALTER TABLE ONLY carto.lines ATTACH PARTITION carto.lines_medium FOR VALUES IN ('medium');

ALTER TABLE ONLY carto.lines ATTACH PARTITION carto.lines_small FOR VALUES IN ('small');

ALTER TABLE ONLY carto.lines ATTACH PARTITION carto.lines_tiny FOR VALUES IN ('tiny');

ALTER TABLE ONLY carto.polygons ATTACH PARTITION carto.polygons_large FOR VALUES IN ('large');

ALTER TABLE ONLY carto.polygons ATTACH PARTITION carto.polygons_medium FOR VALUES IN ('medium');

ALTER TABLE ONLY carto.polygons ATTACH PARTITION carto.polygons_small FOR VALUES IN ('small');

ALTER TABLE ONLY carto.polygons ATTACH PARTITION carto.polygons_tiny FOR VALUES IN ('tiny');

ALTER TABLE ONLY carto.polygons
    ADD CONSTRAINT polygons_unique UNIQUE (map_id, scale);

ALTER TABLE ONLY carto.polygons_large
    ADD CONSTRAINT polygons_large_map_id_scale_key UNIQUE (map_id, scale);

ALTER TABLE ONLY carto.polygons
    ADD CONSTRAINT polygons_pkey PRIMARY KEY (map_id, scale);

ALTER TABLE ONLY carto.polygons_large
    ADD CONSTRAINT polygons_large_pkey PRIMARY KEY (map_id, scale);

ALTER TABLE ONLY carto.polygons_medium
    ADD CONSTRAINT polygons_medium_map_id_scale_key UNIQUE (map_id, scale);

ALTER TABLE ONLY carto.polygons_medium
    ADD CONSTRAINT polygons_medium_pkey PRIMARY KEY (map_id, scale);

ALTER TABLE ONLY carto.polygons_small
    ADD CONSTRAINT polygons_small_map_id_scale_key UNIQUE (map_id, scale);

ALTER TABLE ONLY carto.polygons_small
    ADD CONSTRAINT polygons_small_pkey PRIMARY KEY (map_id, scale);

ALTER TABLE ONLY carto.polygons_tiny
    ADD CONSTRAINT polygons_tiny_map_id_scale_key UNIQUE (map_id, scale);

ALTER TABLE ONLY carto.polygons_tiny
    ADD CONSTRAINT polygons_tiny_pkey PRIMARY KEY (map_id, scale);

CREATE INDEX carto_polygons_geom_gist ON ONLY carto.polygons USING gist (geom);

CREATE INDEX flat_large_geom_idx ON carto.flat_large USING gist (geom);

CREATE INDEX flat_large_map_id_idx ON carto.flat_large USING btree (map_id);

CREATE INDEX large_geom_idx ON carto.polygons_large USING gist (geom);

CREATE INDEX large_map_id_idx ON carto.polygons_large USING btree (map_id);

CREATE INDEX large_new_geom_idx ON carto.large USING gist (geom);

CREATE INDEX large_new_map_id_idx ON carto.large USING btree (map_id);

CREATE INDEX lines_large_geom_idx ON carto.lines_large USING gist (geom);

CREATE INDEX lines_large_line_id_idx ON carto.lines_large USING btree (line_id);

CREATE INDEX lines_large_new_geom_idx1 ON carto.lines_large USING gist (geom);

CREATE INDEX lines_large_new_line_id_idx1 ON carto.lines_large USING btree (line_id);

CREATE INDEX lines_medium_geom_idx ON carto.lines_medium USING gist (geom);

CREATE INDEX lines_medium_line_id_idx ON carto.lines_medium USING btree (line_id);

CREATE INDEX lines_medium_new_geom_idx1 ON carto.lines_medium USING gist (geom);

CREATE INDEX lines_medium_new_line_id_idx1 ON carto.lines_medium USING btree (line_id);

CREATE INDEX lines_small_geom_idx ON carto.lines_small USING gist (geom);

CREATE INDEX lines_small_line_id_idx ON carto.lines_small USING btree (line_id);

CREATE INDEX lines_small_new_geom_idx1 ON carto.lines_small USING gist (geom);

CREATE INDEX lines_small_new_line_id_idx1 ON carto.lines_small USING btree (line_id);

CREATE INDEX lines_tiny_geom_idx ON carto.lines_tiny USING gist (geom);

CREATE INDEX lines_tiny_line_id_idx ON carto.lines_tiny USING btree (line_id);

CREATE INDEX lines_tiny_new_geom_idx1 ON carto.lines_tiny USING gist (geom);

CREATE INDEX lines_tiny_new_line_id_idx1 ON carto.lines_tiny USING btree (line_id);

CREATE INDEX medium_geom_idx ON carto.polygons_medium USING gist (geom);

CREATE INDEX medium_map_id_idx ON carto.polygons_medium USING btree (map_id);

CREATE INDEX medium_new_geom_idx ON carto.medium USING gist (geom);

CREATE INDEX medium_new_map_id_idx ON carto.medium USING btree (map_id);

CREATE INDEX small_geom_idx ON carto.polygons_small USING gist (geom);

CREATE INDEX small_map_id_idx ON carto.polygons_small USING btree (map_id);

CREATE INDEX small_new_geom_idx ON carto.small USING gist (geom);

CREATE INDEX small_new_map_id_idx ON carto.small USING btree (map_id);

CREATE INDEX tiny_geom_idx ON carto.polygons_tiny USING gist (geom);

CREATE INDEX tiny_map_id_idx ON carto.polygons_tiny USING btree (map_id);

CREATE INDEX tiny_new_geom_idx ON carto.tiny USING gist (geom);

CREATE INDEX tiny_new_map_id_idx ON carto.tiny USING btree (map_id);

ALTER INDEX carto.carto_polygons_geom_gist ATTACH PARTITION carto.large_geom_idx;

ALTER INDEX carto.carto_polygons_geom_gist ATTACH PARTITION carto.medium_geom_idx;

ALTER INDEX carto.polygons_unique ATTACH PARTITION carto.polygons_large_map_id_scale_key;

ALTER INDEX carto.polygons_pkey ATTACH PARTITION carto.polygons_large_pkey;

ALTER INDEX carto.polygons_unique ATTACH PARTITION carto.polygons_medium_map_id_scale_key;

ALTER INDEX carto.polygons_pkey ATTACH PARTITION carto.polygons_medium_pkey;

ALTER INDEX carto.polygons_unique ATTACH PARTITION carto.polygons_small_map_id_scale_key;

ALTER INDEX carto.polygons_pkey ATTACH PARTITION carto.polygons_small_pkey;

ALTER INDEX carto.polygons_unique ATTACH PARTITION carto.polygons_tiny_map_id_scale_key;

ALTER INDEX carto.polygons_pkey ATTACH PARTITION carto.polygons_tiny_pkey;

ALTER INDEX carto.carto_polygons_geom_gist ATTACH PARTITION carto.small_geom_idx;

ALTER INDEX carto.carto_polygons_geom_gist ATTACH PARTITION carto.tiny_geom_idx;

ALTER TABLE carto.lines
    ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);

ALTER TABLE carto.polygons
    ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);

GRANT SELECT ON TABLE carto.flat_large TO macrostrat;

GRANT SELECT ON TABLE carto.flat_medium TO macrostrat;

GRANT SELECT ON TABLE carto.large TO macrostrat;

GRANT SELECT ON TABLE carto.medium TO macrostrat;

GRANT SELECT ON TABLE carto.small TO macrostrat;

GRANT SELECT ON TABLE carto.tiny TO macrostrat;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat_admin IN SCHEMA carto GRANT SELECT,USAGE ON SEQUENCES  TO macrostrat;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat_admin IN SCHEMA carto GRANT SELECT ON TABLES  TO macrostrat;

