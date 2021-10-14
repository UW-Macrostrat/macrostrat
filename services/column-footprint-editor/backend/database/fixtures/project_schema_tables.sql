CREATE SCHEMA IF NOT EXISTS ${project_schema};

create table if not exists ${project_schema}.column_groups(
    id SERIAL PRIMARY KEY,
    col_group_id integer,
    col_group text,
    col_group_name text
);

CREATE TABLE IF NOT EXISTS ${project_schema}.columns(
    id serial PRIMARY KEY,
    project_id integer,
    col_id integer,
    col_name text,
    col_group integer REFERENCES ${project_schema}.column_groups(id),
    location geometry 
);
