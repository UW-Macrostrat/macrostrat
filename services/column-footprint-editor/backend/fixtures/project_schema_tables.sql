CREATE SCHEMA IF NOT EXISTS ${project_schema};

CREATE TABLE IF NOT EXISTS ${project_schema}.columns(
    id serial PRIMARY KEY,
    project_id integer,
    col_id integer,
    col_name text,
    col_group integer REFERENCES column_groups(id),
    location geometry 
);