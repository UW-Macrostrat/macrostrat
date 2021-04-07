/*
Right now start off with 1 table..
*/
CREATE EXTENSION postgis;

CREATE TABLE IF NOT EXISTS column_topology(
    id serial PRIMARY KEY,
    project_id integer,
    col_name text,
    col_group text,
    location geometry 
);