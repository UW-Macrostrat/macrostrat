CREATE SCHEMA IF NOT EXISTS user_features;
--changed map_layers from enum to array in order to save multiple layers at a time

create table IF NOT EXISTS user_features.user_locations
(
    id              serial primary key,
    user_id         integer not null constraint fk_user references macrostrat_auth."user" on delete cascade,
    name            varchar(120) not null,
    description     text,
    point           public.geometry(POINT, 4326),
    zoom            numeric,
    meters_from_point   numeric,
    elevation       numeric,
    azimuth         numeric,
    pitch           numeric,
    map_layers      text [],
    created_at      timestamp default now() not null,
    updated_at      timestamp default now() not null
);


create table IF NOT EXISTS user_features.location_tags
(
    id          serial PRIMARY KEY,
    name        varchar(120) not NULL,
    description text,
    color       varchar(30)
);

--intersection table for ids joins with the location_tags table
--remove category and add NULL user_ids
create table IF NOT EXISTS user_features.location_tags_intersect (
    tag_id      integer constraint fk_tag_id references user_features."location_tags" on delete cascade,
    user_id     integer constraint fk_user_id references macrostrat_auth."user" on delete cascade,
    location_id integer not null constraint fk_location_id references user_features."user_locations" on delete cascade,
    PRIMARY KEY (tag_id, user_id, location_id)
);


alter table user_features.user_locations owner to "macrostrat";
alter table user_features.location_tags owner to "macrostrat";
alter table user_features.location_tags_intersect owner to "macrostrat";

grant delete, insert, select, update on user_features.user_locations to web_anon;
grant delete, insert, select, update on user_features.location_tags to web_anon;
GRANT USAGE, SELECT ON SEQUENCE user_features.user_locations_id_seq TO web_anon;

grant delete, insert, select, update on user_features.user_locations to web_user;
grant delete, insert, select, update on user_features.location_tags to web_user;
GRANT USAGE, SELECT ON SEQUENCE user_features.user_locations_id_seq TO web_anon;


CREATE OR REPLACE VIEW macrostrat_api.user_locations AS
SELECT *
FROM user_features.user_locations;


CREATE OR REPLACE VIEW macrostrat_api.location_tags AS
SELECT *
FROM user_features.location_tags;

--this will change from web_anon to an authorized user once that workflow has been implemented.
--web_anon is used for testing only right now.
GRANT SELECT, INSERT, UPDATE, DELETE ON macrostrat_api.user_locations TO web_anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON macrostrat_api.location_tags TO web_anon;


NOTIFY pgrst, 'reload schema';










