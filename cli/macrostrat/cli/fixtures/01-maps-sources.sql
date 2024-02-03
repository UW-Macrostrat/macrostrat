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

CREATE OR REPLACE VIEW maps.sources_meta
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
    status_code
FROM maps.sources
ORDER BY source_id DESC;

COMMENT ON VIEW maps.sources_meta IS 'Convenience view for maps.sources with only metadata fields';