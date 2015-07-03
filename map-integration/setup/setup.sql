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
  lith_nlp json,
  descrip text,
  descrip_nlp json,
  comments text,
  comments_nlp json,
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
  lith_nlp json,
  descrip text,
  descrip_nlp json,
  comments text,
  comments_nlp json,
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
  lith_nlp json,
  descrip text,
  descrip_nlp json,
  comments text,
  comments_nlp json,
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


SELECT UpdateGeometrySRID('maps', 'small', 'geom', 4326);
SELECT UpdateGeometrySRID('maps', 'medium', 'geom', 4326);
SELECT UpdateGeometrySRID('maps', 'large', 'geom', 4326);

ALTER TABLE maps.small ADD CONSTRAINT enforce_valid_geom_small CHECK (st_isvalid(geom));
ALTER TABLE maps.medium ADD CONSTRAINT enforce_valid_geom_medium CHECK (st_isvalid(geom));
ALTER TABLE maps.large ADD CONSTRAINT enforce_valid_geom_large CHECK (st_isvalid(geom));

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
