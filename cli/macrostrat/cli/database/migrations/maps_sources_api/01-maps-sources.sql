DROP VIEW IF EXISTS macrostrat_api.sources_ingestion;
DROP VIEW IF EXISTS macrostrat_api.sources_metadata CASCADE;
DROP VIEW IF EXISTS maps.sources_metadata CASCADE;
DROP VIEW IF EXISTS macrostrat_api.sources;

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
    license,
    features,
    area,
    display_scales,
    new_priority priority,
    status_code,
    raster_url,
    scale_denominator,
    is_finalized,
    lines_oriented
FROM maps.sources AS s
ORDER BY source_id DESC;

COMMENT ON VIEW maps.sources_metadata IS 'Convenience view for maps.sources with only metadata fields';

CREATE OR REPLACE VIEW macrostrat_api.sources_metadata AS
SELECT *,
  -- Legacy column for backwards compatibility.
  is_finalized is_mapped
FROM maps.sources_metadata;

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
    s.license,
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
    i.map_id,
    s.is_finalized,
    s.scale_denominator
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
    s.license,
    s.scale,
    s.features,
    s.area,
    s.display_scales,
    s.priority,
    s.status_code,
    s.raster_url,
    s.web_geom envelope,
    s.is_finalized,
    s.scale_denominator,
    s.lines_oriented
FROM maps.sources s;
