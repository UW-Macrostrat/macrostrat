CREATE SCHEMA IF NOT EXISTS user_features;
--changed map_layers from enum to array in order to save multiple layers at a time
CREATE EXTENSION IF NOT EXISTS postgis;       -- requires superuser

create table IF NOT EXISTS user_features.user_locations
(
  --instead of serial for id, we want GENERATED ALWAYS AS IDENTITY so that postgrest can handle the id increments internally and
  --we don't have to rely on granting sequence id access to the base table to web_user.
  --Goal is to try to keep grant access to web_user on the views only rather than the base tables.
  --removed DEFAULT current_app_user_id()
    id              integer GENERATED ALWAYS AS IDENTITY primary key,
    user_id         integer null constraint fk_user references macrostrat_auth."user" on delete cascade,
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
INSERT INTO user_features.user_locations
        (user_id,
         name,
         description,
         point,                  -- geometry(POINT,4326)
         zoom,
         meters_from_point,
         elevation,
         azimuth,
         pitch,
         map_layers)
VALUES
/* ——— user_id = 46 (four rows) ——— */
(46, 'Grand Canyon – Cape Royal',        'Test row for user 46 (A)',
 'SRID=4326;POINT(-111.9470 36.1851)', 13, 800, 2438, 160, -15,
 ARRAY['bedrock','contacts','faults']),

(46, 'Yosemite – Glacier Point',         'Test row for user 46 (B)',
 'SRID=4326;POINT(-119.5738 37.7303)', 14, 600, 2199, 100, -12,
 ARRAY['bedrock','glaciers']),

(46, 'Capitol Reef – Hickman Bridge',    'Test row for user 46 (C)',
 'SRID=4326;POINT(-111.2462 38.2927)', 15, 300, 1628, 140,  -8,
 ARRAY['bedrock','contacts']),

(46, 'Death Valley – Dante’s View',      'Test row for user 46 (D)',
 'SRID=4326;POINT(-116.7080 36.2292)', 12, 750, 1675, 185, -10,
 ARRAY['bedrock','contacts','faults']),

/* ——— remaining user_ids ——— */
( 1, 'Pilot Mountain',                   'Sample for user 1',
 'SRID=4326;POINT(-80.4670 36.3410)', 12, 400,  900,  45,  -6,
 ARRAY['bedrock']),

( 2, 'Mt Rainier – Sunrise',             'Sample for user 2',
 'SRID=4326;POINT(-121.6400 46.9110)', 11, 500, 1950,  90,  -8,
 ARRAY['bedrock','glaciers']),

( 3, 'Zion – Angel''s Landing',          'Sample for user 3',
 'SRID=4326;POINT(-113.0263 37.2692)', 15, 200, 1765, 270, -14,
 ARRAY['bedrock','contacts']),

( 4, 'Mesa Verde – Cliff Palace',        'Sample for user 4',
 'SRID=4326;POINT(-108.4618 37.1606)', 16, 150, 2073, 190,  -5,
 ARRAY['bedrock']),

( 5, 'Mt Whitney Trailhead',             'Sample for user 5',
 'SRID=4326;POINT(-118.2386 36.5785)', 13, 600, 2550,  85,  -9,
 ARRAY['bedrock','faults']),

( 6, 'Acadia – Cadillac Mountain',       'Sample for user 6',
 'SRID=4326;POINT(-68.2250 44.3519)', 12, 350,  466, 110,  -4,
 ARRAY['bedrock']),

(10, 'Rocky Mtn – Trail Ridge',          'Sample for user 10',
 'SRID=4326;POINT(-105.7440 40.4350)', 12, 700, 3650, 210, -11,
 ARRAY['bedrock','contacts']),

(11, 'Everglades – Shark Valley',        'Sample for user 11',
 'SRID=4326;POINT(-80.7653 25.7580)', 11, 500,    3,  45,  -2,
 ARRAY['contacts']),

(12, 'Mt St Helens – Johnston Ridge',    'Sample for user 12',
 'SRID=4326;POINT(-122.2190 46.2750)', 14, 650, 1280, 320,  -7,
 ARRAY['bedrock','glaciers','faults']),

(13, 'Death Valley – Badwater',          'Sample for user 13',
 'SRID=4326;POINT(-116.8252 36.2503)', 14, 700,  -86, 200,  -4,
 ARRAY['bedrock','contacts','faults']),

(47, 'Mt Hood – Timberline Lodge',       'Sample for user 47',
 'SRID=4326;POINT(-121.6990 45.3310)', 13, 550, 1816, 180,  -9,
 ARRAY['bedrock','glaciers']);





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

--grant select/read on all columns
GRANT SELECT ON user_features.user_locations TO web_user;
--grant insert,update,delete only on mutable columns
GRANT INSERT (user_id, name, description, point, zoom,
              meters_from_point, elevation, azimuth,
              pitch, map_layers) ON user_features.user_locations TO web_user;
GRANT UPDATE (user_id, name, description, point, zoom,
              meters_from_point, elevation, azimuth,
              pitch, map_layers) ON user_features.user_locations TO web_user;
GRANT DELETE ON user_features.user_locations TO web_user;
