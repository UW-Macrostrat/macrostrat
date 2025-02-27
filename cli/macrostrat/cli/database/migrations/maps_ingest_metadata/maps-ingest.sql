DROP VIEW IF EXISTS macrostrat_api.map_ingest_metadata;

ALTER TABLE maps_metadata.ingest_process ADD COLUMN polygon_state jsonb;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN line_state jsonb;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN point_state jsonb;

CREATE OR REPLACE VIEW macrostrat_api.map_ingest_metadata AS
SELECT * FROM maps_metadata.ingest_process;

-- Make it writeable by users
GRANT SELECT, UPDATE ON maps_metadata.ingest_process TO web_user;
GRANT SELECT, UPDATE ON macrostrat_api.map_ingest_metadata TO web_user;
