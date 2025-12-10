DROP VIEW IF EXISTS macrostrat_api.map_ingest_metadata;

ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS polygon_state jsonb;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS line_state jsonb;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS point_state jsonb;

ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS ingest_pipeline text;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS map_url text;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS ingested_by text;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS slug text;


CREATE OR REPLACE VIEW macrostrat_api.map_ingest_metadata AS
SELECT * FROM maps_metadata.ingest_process;

-- Make it writeable by users
GRANT SELECT, UPDATE ON maps_metadata.ingest_process TO web_user;
GRANT SELECT, UPDATE ON macrostrat_api.map_ingest_metadata TO web_user;

