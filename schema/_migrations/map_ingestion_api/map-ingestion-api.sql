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
DROP VIEW IF EXISTS map_ingestion_api.maps;
CREATE OR REPLACE VIEW map_ingestion_api.maps AS
SELECT
  s.source_id,
  s.slug,
  name,
  url,
  ref_year,
  scale,
  i.state,
  (SELECT array_agg(tag) AS tags FROM maps_metadata.ingest_process_tag WHERE ingest_process_id = i.id) AS tags
FROM maps.sources s
LEFT JOIN maps_metadata.ingest_process i
  ON s.source_id = i.source_id
ORDER BY s.source_id DESC;

