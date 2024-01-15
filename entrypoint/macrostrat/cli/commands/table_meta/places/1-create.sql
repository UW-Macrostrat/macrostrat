
CREATE TABLE macrostrat.places_new (
    place_id integer PRIMARY KEY,
    name text,
    abbrev text,
    postal text,
    country text,
    country_abbrev text,
    geom geometry
);

