CREATE DATABASE burwell;

\connect burwell;

CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;


CREATE SCHEMA maps;
CREATE SCHEMA lines;
CREATE SCHEMA sources;
CREATE SCHEMA macrostrat;

/* Used for creating lookup_tables */
DROP AGGREGATE IF EXISTS array_agg_mult (anyarray);
CREATE AGGREGATE array_agg_mult (anyarray)  (
    SFUNC     = array_cat
   ,STYPE     = anyarray
   ,INITCOND  = '{}'
);

/* Use this so that map_id is unique across all three tables */
CREATE SEQUENCE map_ids INCREMENT 1 START 1;

/* Use this so that line_id is unique across all three tables */
CREATE SEQUENCE line_ids INCREMENT 1 START 1;

CREATE TABLE maps.small (
  map_id integer DEFAULT nextval('map_ids') PRIMARY KEY,
  orig_id integer,
  source_id integer,
  name character varying(255),
  strat_name character varying(255),
  age character varying(255),
  lith text,
  lith_nlp json,
  descrip text,
  descrip_nlp json,
  comments text,
  comments_nlp json,
  t_interval integer NOT NULL,
  b_interval integer NOT NULL,
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
  lith_nlp json,
  descrip text,
  descrip_nlp json,
  comments text,
  comments_nlp json,
  t_interval integer NOT NULL,
  b_interval integer NOT NULL,
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
  lith_nlp json,
  descrip text,
  descrip_nlp json,
  comments text,
  comments_nlp json,
  t_interval integer NOT NULL,
  b_interval integer NOT NULL,
  geom geometry
);

CREATE TABLE maps.sources (
  source_id serial,
  name varchar(255),
  primary_table varchar(50),
  url varchar(255),
  ref_title text,
  authors varchar(255),
  ref_year smallint,
  ref_source varchar(255),
  isbn_doi varchar(100),
  scale varchar(20),
  features integer,
  area decimal,
  bbox geometry
);

CREATE TABLE maps.map_liths (
  map_id integer NOT NULL,
  lith_id integer NOT NULL,
  basis_col character varying(50)
);

CREATE TABLE maps.map_strat_names (
  map_id integer NOT NULL,
  strat_name_id integer NOT NULL,
  basis_col character varying(50)
);

CREATE TABLE maps.map_units (
  map_id integer NOT NULL,
  unit_id integer NOT NULL,
  basis_col character varying(50)
);

CREATE TABLE lines.small (
  line_id integer DEFAULT nextval('line_ids') PRIMARY KEY,
  orig_id integer,
  source_id integer,
  name character varying(255),
  type character varying(100),
  direction character varying(20),
  descrip text,
  geom geometry
);

CREATE TABLE lines.medium (
  line_id integer DEFAULT nextval('line_ids') PRIMARY KEY,
  orig_id integer,
  source_id integer,
  name character varying(255),
  type character varying(100),
  direction character varying(20),
  descrip text,
  geom geometry
);

CREATE TABLE lines.large (
  line_id integer DEFAULT nextval('line_ids') PRIMARY KEY,
  orig_id integer,
  source_id integer,
  name character varying(255),
  type character varying(100),
  direction character varying(20),
  descrip text,
  geom geometry
);

SELECT UpdateGeometrySRID('maps', 'small', 'geom', 4326);
SELECT UpdateGeometrySRID('maps', 'medium', 'geom', 4326);
SELECT UpdateGeometrySRID('maps', 'large', 'geom', 4326);

SELECT UpdateGeometrySRID('lines', 'small', 'geom', 4326);
SELECT UpdateGeometrySRID('lines', 'medium', 'geom', 4326);
SELECT UpdateGeometrySRID('lines', 'large', 'geom', 4326);

ALTER TABLE maps.small ADD CONSTRAINT enforce_valid_geom_small CHECK (st_isvalid(geom));
ALTER TABLE maps.medium ADD CONSTRAINT enforce_valid_geom_medium CHECK (st_isvalid(geom));
ALTER TABLE maps.large ADD CONSTRAINT enforce_valid_geom_large CHECK (st_isvalid(geom));

ALTER TABLE lines.small ADD CONSTRAINT enforce_valid_geom_lines_small CHECK (st_isvalid(geom));
ALTER TABLE lines.medium ADD CONSTRAINT enforce_valid_geom_lines_medium CHECK (st_isvalid(geom));
ALTER TABLE lines.large ADD CONSTRAINT enforce_valid_geom_lines_large CHECK (st_isvalid(geom));

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

CREATE INDEX ON lines.small (line_id);
CREATE INDEX ON lines.small (orig_id);
CREATE INDEX ON lines.small (source_id);
CREATE INDEX ON lines.small USING Gist (geom);

CREATE INDEX ON lines.medium (line_id);
CREATE INDEX ON lines.medium (orig_id);
CREATE INDEX ON lines.medium (source_id);
CREATE INDEX ON lines.medium USING Gist (geom);

CREATE INDEX ON lines.large (line_id);
CREATE INDEX ON lines.large (orig_id);
CREATE INDEX ON lines.large (source_id);
CREATE INDEX ON lines.large USING Gist (geom);
