CREATE SCHEMA user_features;

CREATE TYPE saved_locations_enum AS ENUM ('Favorites', 'Want to go', 'Geological wonder');

-- auto-generated definition
create table saved_locations
(
    id                   serial
        primary key,
    user_id              integer                 not null
        constraint fk_user
            references macrostrat_auth."user",
    location_name        varchar(120)            not null,
    location_description text,
    latitude             numeric                 not null,
    longitude            numeric                 not null,
    created_at           timestamp default now() not null,
    updated_at           timestamp default now() not null,
    category             saved_locations_enum
);

alter table saved_locations
    owner to "macrostrat-admin";

grant delete, insert, select, update on saved_locations to web_anon;

grant delete, insert, select, update on saved_locations to web_user;





