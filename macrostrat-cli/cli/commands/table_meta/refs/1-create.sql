
CREATE TABLE macrostrat.refs_new (
    id integer PRIMARY key,
    pub_year integer,
    author character varying(255),
    ref text,
    doi character varying(40),
    compilation_code character varying(100),
    url text,
    rgeom geometry
);

