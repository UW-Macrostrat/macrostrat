CREATE DATABASE elevation;

\connect elevation;

CREATE EXTENSION postgis;

CREATE SCHEMA sources;

CREATE TABLE sources (
  elev_id serial,
  name varchar(255),
  primary_table varchar(50),
  url varchar(255),
  ref_title text,
  authors varchar(255),
  ref_year smallint,
  ref_source varchar(255),
  isbn_doi varchar(100),
  scale varchar(20)
);
