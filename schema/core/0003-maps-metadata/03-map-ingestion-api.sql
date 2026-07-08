CREATE SCHEMA IF NOT EXISTS map_ingestion_api;

CREATE OR REPLACE VIEW map_ingestion_api.line_types AS
SELECT type, count(*) FROM maps.lines
WHERE type IS NOT null
GROUP BY type
ORDER BY count(*) DESC;

CREATE OR REPLACE VIEW map_ingestion_api.point_types AS
SELECT point_type, count(*) FROM maps.points
WHERE point_type IS NOT null
GROUP BY point_type
ORDER BY count(*) DESC;

-- Correct a small data error
UPDATE maps.lines SET type = 'strike-slip fault'
WHERE type = 'strike-slilp fault';

-- Create another view for api
CREATE OR REPLACE VIEW map_ingestion_api.maps AS
WITH tags AS (
  SELECT ingest_process_id, array_agg(tag)::text[] names FROM maps_metadata.ingest_process_tag
  GROUP BY ingest_process_id
)
SELECT
  s.source_id,
  s.slug,
  name,
  url,
  ref_year,
  scale,
  i.state,
  coalesce(tags.names, ARRAY[]::text[]) AS tags
FROM maps.sources s
LEFT JOIN maps_metadata.ingest_process i
  ON s.source_id = i.source_id
ORDER BY s.source_id DESC;

