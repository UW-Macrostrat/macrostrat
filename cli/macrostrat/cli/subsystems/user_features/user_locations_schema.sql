CREATE SCHEMA user_features;

CREATE TYPE location_type AS ENUM ('Favorites', 'Want to go', 'Geological wonder');

create table user_locations
(
    id                   serial
        primary key,
    user_id              integer                 not null
        constraint fk_user
            references macrostrat_auth."user",
    name        varchar(120)            not null,
    description text,
    latitude             numeric                 not null,
    longitude            numeric                 not null,
    created_at           timestamp default now() not null,
    updated_at           timestamp default now() not null,
    category             location_type,
    orientation_details  text
);

create table location_tags
(
    id      serial PRIMARY KEY,
    user_id integer not null constraint fk_user_id REFERENCES macrostrat_auth."user",
    location_id integer not null constraint fk_location_id REFERENCES user_features."user_locations",
    name    varchar(120) not NULL,
    description text,
    color   varchar(30)
);

alter table user_locations
    owner to "macrostrat-admin";

grant delete, insert, select, update on user_locations to web_anon;

grant delete, insert, select, update on user_locations to web_user;





