create table if not exists projects(
    project_id integer PRIMARY KEY,
    name text,
    description text
);

create table if not exists column_groups(
    id SERIAL PRIMARY KEY,
    col_group_id integer,
    col_group text,
    col_group_name text
);