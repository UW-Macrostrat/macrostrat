ALTER TABLE maps.sources ADD COLUMN IF NOT EXISTS raster_url text;

DROP VIEW IF EXISTS maps.sources_metadata CASCADE;
CREATE OR REPLACE VIEW maps.sources_metadata AS
SELECT
    s.source_id,
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
    raster_url,
    CASE
       WHEN psi.source_id IS NULL THEN false
       ELSE true
    END AS is_mapped
FROM maps.sources AS s
LEFT JOIN (
    SELECT
        DISTINCT(polygons.source_id)
    FROM maps.polygons
) psi ON s.source_id = psi.source_id
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
JOIN maps_metadata.ingest_process i
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
<<<<<<< HEAD:cli/macrostrat/cli/database/migrations/map_sources/01-maps-sources.sql

-- This is a hack and should be handled centrally. Declarative role management?
GRANT USAGE ON SCHEMA macrostrat_api TO web_anon;
GRANT USAGE ON SCHEMA macrostrat_api TO web_user;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat_api TO web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat_api TO web_user;
=======
>>>>>>> main:cli/macrostrat/cli/fixtures/01-maps-sources.sql
