CREATE SCHEMA IF NOT EXISTS {project_schema};

create table if not exists {project_schema}.column_groups(
    id SERIAL PRIMARY KEY,
    col_group_id integer,
    col_group text,
    col_group_name text,
    color text
);

CREATE TABLE IF NOT EXISTS {project_schema}.columns(
    id serial PRIMARY KEY,
    project_id integer,
    col_group integer REFERENCES {project_schema}.column_groups(id),
    col_id integer,
    col_name text,
    description text,
    point geometry,
    location geometry
);
