/*
Right now start off with 1 table..
*/
CREATE EXTENSION postgis;

CREATE SCHEMA IF NOT EXISTS columns

CREATE TABLE IF NOT EXISTS columns(
    id serial PRIMARY KEY,
    project_id integer,
    col_id integer,
    col_name text,
    col_group text,
    location geometry 
);