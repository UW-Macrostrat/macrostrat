ALTER TABLE maps_metadata.ingest_process ADD COLUMN ui_state jsonb;

CREATE OR REPLACE VIEW macrostrat_api.map_ingest_metadata AS
SELECT * FROM maps_metadata.ingest_process;
