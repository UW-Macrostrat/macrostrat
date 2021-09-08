/*
Right now start off with 1 table..
*/
CREATE EXTENSION postgis;

CREATE SCHEMA IF NOT EXISTS ${project_schema}

CREATE TABLE IF NOT EXISTS ${project_schema}.columns(
    id serial PRIMARY KEY,
    project_id integer,
    col_id integer,
    col_name text,
    col_group text,
    location geometry 
);