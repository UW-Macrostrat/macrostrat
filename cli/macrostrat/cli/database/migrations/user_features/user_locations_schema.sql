CREATE SCHEMA IF NOT EXISTS user_features;
--changed map_layers from enum to array in order to save multiple layers at a time

create table IF NOT EXISTS user_features.user_locations
(
  --instead of serial for id, we want GENERATED ALWAYS AS IDENTITY so that postgrest can handle the id increments internally and
  --we don't have to rely on granting sequence id access to the base table to web_user.
  --Goal is to try to keep grant access to web_user on the views only rather than the base tables.
  --removed DEFAULT current_app_user_id()
    id              integer GENERATED ALWAYS AS IDENTITY primary key,
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

--add predefined list of tags for users to use
create table IF NOT EXISTS user_features.location_tags
(
    id          serial PRIMARY KEY,
    name        varchar(120) not NULL,
    description text,
    color       varchar(30)
);

INSERT INTO user_features.location_tags (name, description, color)
VALUES
  ('Basalt Outcrop',      'Exposure of dark, fine‑grained basaltic lava',          '#4B4E6D'),
  ('Fossil Locality',     'Site where macro‑ or microfossils have been collected', '#C19A6B'),
  ('Fault Trace',         'Mapped surface expression of a fault plane',            '#FF6F61'),
  ('Glacial Erratic',     'Large exotic boulder deposited by glacial ice',         '#3DA5D9'),
  ('Mineral Prospect',    'Area under evaluation for economic mineralization',     '#FFD166'),
  ('Stratotype Section',  'Formally designated reference stratigraphic section',   '#6D8B74'),
  ('Core Sample Site',    'Location where drill‑core was extracted',               '#8E7DBE'),
  ('Hydrothermal Vent',   'Vent or fissure of hydrothermal fluids (active/pale)',  '#E9724C'),
  ('Paleosol Horizon',    'Profile of an ancient soil preserved in the rock record','#A67C52'),
  ('Dike Intrusion',      'Tabular igneous body cutting host strata',              '#FFB3BA');


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
