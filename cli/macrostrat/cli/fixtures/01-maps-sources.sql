CREATE TABLE maps.sources (
    source_id integer DEFAULT nextval('maps.sources_source_id_seq'::regclass) UNIQUE PRIMARY KEY,
    name character varying(255),
    primary_table character varying(255) UNIQUE,
    url character varying(255),
    ref_title text,
    authors character varying(255),
    ref_year text,
    ref_source character varying(255),
    isbn_doi character varying(100),
    scale character varying(20),
    primary_line_table character varying(50),
    licence character varying(100),
    features integer,
    area integer,
    priority boolean DEFAULT false,
    rgeom geometry,
    display_scales text[],
    web_geom geometry,
    new_priority integer DEFAULT 0,
    status_code text DEFAULT 'active'::text,
    slug text NOT NULL UNIQUE
);
COMMENT ON COLUMN maps.sources.slug IS 'Unique identifier for each Macrostrat source';

ALTER TABLE maps.sources ADD COLUMN IF NOT EXISTS raster_url text;

DROP VIEW maps.sources_metadata CASCADE;
CREATE OR REPLACE VIEW maps.sources_metadata AS
SELECT
    source_id,
    slug,
    name,
    url,
    ref_title,
    authors,
    ref_year,
    ref_source,
    isbn_doi,
    scale,
    licence,
    features,
    area,
    display_scales,
    new_priority priority,
    status_code,
    raster_url
FROM maps.sources
ORDER BY source_id DESC;

COMMENT ON VIEW maps.sources_metadata IS 'Convenience view for maps.sources with only metadata fields';

CREATE OR REPLACE VIEW macrostrat_api.sources_metadata AS
SELECT * FROM maps.sources_metadata;

CREATE OR REPLACE VIEW macrostrat_api.sources_ingestion AS
SELECT
    s.source_id,
    s.slug,
    s.name,
    s.url,
    s.ref_title,
    s.authors,
    s.ref_year,
    s.ref_source,
    s.isbn_doi,
    s.scale,
    s.licence,
    s.features,
    s.area,
    s.display_scales,
    s.priority,
    s.status_code,
    s.raster_url,
    i.state,
    i.comments,
    i.created_on,
    i.completed_on,
    i.map_id
FROM maps.sources_metadata s
JOIN macrostrat.ingest_process i
  ON i.source_id = s.source_id;

CREATE OR REPLACE VIEW macrostrat_api.sources AS
SELECT
    s.source_id,
    s.slug,
    s.name,
    s.url,
    s.ref_title,
    s.authors,
    s.ref_year,
    s.ref_source,
    s.isbn_doi,
    s.licence,
    s.scale,
    s.features,
    s.area,
    s.display_scales,
    s.priority,
    s.status_code,
    s.raster_url,
    s.web_geom envelope
FROM maps.sources s;

-- This is a hack and should be handled centrally. Declarative role management?
GRANT USAGE ON SCHEMA macrostrat_api TO web_anon;
GRANT USAGE ON SCHEMA macrostrat_api TO web_user;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat_api TO web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat_api TO web_user;