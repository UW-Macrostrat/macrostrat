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
  name character varying(255),
  age character varying(255),
  descrip text,
  comments text,
  t_interval integer,
  b_interval integer
);

CREATE TABLE maps.medium (
  mmap_id integer DEFAULT nextval('map_ids') PRIMARY KEY,
  name character varying(255),
  age character varying(255),
  descrip text,
  comments text,
  t_interval integer,
  b_interval integer
);

CREATE TABLE maps.large (
  map_id integer DEFAULT nextval('map_ids') PRIMARY KEY,
  name character varying(255),
  age character varying(255),
  descrip text,
  comments text,
  t_interval integer,
  b_interval integer
);

CREATE TABLE maps.source_links (
  map_id integer,
  orig_id integer,
  source_id integer
);

CREATE TABLE maps.sources (
  source_id serial,
  name varchar(255),
  primary_table varchar(255)
);

CREATE TABLE maps.map_liths (
  map_id integer NOT NULL,
  lith_id integer NOT NULL
);

CREATE TABLE maps.map_strat_names (
  map_id integer NOT NULL,
  strat_name_id integer NOT NULL
);

CREATE TABLE maps.map_units (
  map_id integer NOT NULL,
  unit_id integer NOT NULL
);
