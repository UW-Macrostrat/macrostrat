CREATE DATABASE burwell;

\connect burwell;

CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;


CREATE SCHEMA maps;
CREATE SCHEMA sources;
CREATE SCHEMA macrostrat;

/* Use this so that map_id is unique across all three tables */
CREATE SEQUENCE map_ids INCREMENT 1 START 1;

CREATE TABLE maps.small (
  map_id integer DEFAULT nextval('map_ids') PRIMARY KEY,
  orig_id integer,
  source_id integer,
  name character varying(255),
  strat_name character varying(255),
  age character varying(255),
  lith text,
  descrip text,
  comments text,
  t_interval integer,
  b_interval integer,
  geom geometry
);

CREATE TABLE maps.medium (
  map_id integer DEFAULT nextval('map_ids') PRIMARY KEY,
  orig_id integer,
  source_id integer,
  name character varying(255),
  strat_name character varying(255),
  age character varying(255),
  lith text,
  descrip text,
  comments text,
  t_interval integer,
  b_interval integer,
  geom geometry
);

CREATE TABLE maps.large (
  map_id integer DEFAULT nextval('map_ids') PRIMARY KEY,
  orig_id integer,
  source_id integer,
  name character varying(255),
  strat_name character varying(255),
  age character varying(255),
  lith text,
  descrip text,
  comments text,
  t_interval integer,
  b_interval integer,
  geom geometry
);

CREATE TABLE maps.sources (
  source_id serial,
  name varchar(255),
  primary_table varchar(255)
);

CREATE TABLE maps.map_liths (
  map_id integer NOT NULL,
  lith_id integer NOT NULL,
  basis_id integer NOT NULL
);

CREATE TABLE maps.map_strat_names (
  map_id integer NOT NULL,
  strat_name_id integer NOT NULL,
  basis_id integer NOT NULL
);

CREATE TABLE maps.map_units (
  map_id integer NOT NULL,
  unit_id integer NOT NULL,
  basis_id integer NOT NULL
);

CREATE TABLE maps.bases (
  basis_id serial PRIMARY KEY NOT NULL,
  name character varying(200)
);

INSERT INTO maps.bases (basis_id, name) VALUES
(0, 'manual-matches'),

(1, 'mbr_name-strat_name'),
(2, 'fm_name-strat_name'),
(3, 'gp_name-strat_name'),
(4, 'sgp_name-strat_name'),

(5, 'mbr_name-name'),
(6, 'fm_name-name'),
(7, 'gp_name-name'),
(8, 'sgp_name-name'),

(9, 'mbr_name-descrip'),
(10, 'fm_name-descrip'),
(11, 'gp_name-descrip'),
(12, 'sgp_name-descrip'),

(13, 'mbr_name-comments'),
(14, 'fm_name-comments'),
(15, 'gp_name-comments'),
(16, 'sgp_name-comments'),

(17, 'ns-mbr_name-strat_name'),
(18, 'ns-fm_name-strat_name'),
(19, 'ns-gp_name-strat_name'),
(20, 'ns-sgp_name-strat_name'),

(21, 'ns-mbr_name-name'),
(22, 'ns-fm_name-name'),
(23, 'ns-gp_name-name'),
(24, 'ns-sgp_name-name'),

(25, 'ns-mbr_name-descrip'),
(26, 'ns-fm_name-descrip'),
(27, 'ns-gp_name-descip'),
(28, 'ns-sgp_name-descrip'),

(29, 'ns-mbr_name-comments'),
(30, 'ns-fm_name-comments'),
(31, 'ns-gp_name-comments'),
(32, 'ns-sgp_name-comments'),
(88, 'misses');


SELECT UpdateGeometrySRID('maps', 'small', 'geom', 4326);
SELECT UpdateGeometrySRID('maps', 'medium', 'geom', 4326);
SELECT UpdateGeometrySRID('maps', 'large', 'geom', 4326);

CREATE INDEX ON maps.small (map_id);
CREATE INDEX ON maps.small (orig_id);
CREATE INDEX ON maps.small (source_id);
CREATE INDEX ON maps.small (t_interval);
CREATE INDEX ON maps.small (b_interval);
CREATE INDEX ON maps.small USING Gist (geom);

CREATE INDEX ON maps.medium (map_id);
CREATE INDEX ON maps.medium (orig_id);
CREATE INDEX ON maps.small (source_id);
CREATE INDEX ON maps.medium (t_interval);
CREATE INDEX ON maps.medium (b_interval);
CREATE INDEX ON maps.medium USING Gist (geom);

CREATE INDEX ON maps.large (map_id);
CREATE INDEX ON maps.large (orig_id);
CREATE INDEX ON maps.small (source_id);
CREATE INDEX ON maps.large (t_interval);
CREATE INDEX ON maps.large (b_interval);
CREATE INDEX ON maps.large USING Gist (geom);

CREATE INDEX ON maps.sources (source_id);

CREATE INDEX ON maps.map_liths (map_id);
CREATE INDEX ON maps.map_liths (lith_id);

CREATE INDEX ON maps.map_strat_names (map_id);
CREATE INDEX ON maps.map_strat_names (strat_name_id);

CREATE INDEX ON maps.map_units (map_id);
CREATE INDEX ON maps.map_units (unit_id);
