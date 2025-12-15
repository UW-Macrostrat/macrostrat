DROP VIEW IF EXISTS macrostrat_api.map_ingest_metadata;
DROP VIEW IF EXISTS maps.ingest_process;

ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS polygon_state jsonb;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS line_state jsonb;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS point_state jsonb;

ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS ingest_pipeline text;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS map_url text;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS ingested_by text;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN IF NOT EXISTS slug text;

ALTER TABLE maps_metadata.ingest_process DROP COLUMN IF EXISTS access_group_id;
ALTER TABLE maps_metadata.ingest_process DROP COLUMN IF EXISTS object_group_id;



CREATE OR REPLACE VIEW maps.ingest_process AS
SELECT * FROM maps_metadata.ingest_process;
CREATE OR REPLACE VIEW macrostrat_api.map_ingest_metadata AS
SELECT * FROM maps_metadata.ingest_process;


-- Make it writeable by users
GRANT SELECT, UPDATE ON maps_metadata.ingest_process TO web_user;
GRANT SELECT, UPDATE ON macrostrat_api.map_ingest_metadata TO web_user;

create view macrostrat_api.map_ingest as
    select * from maps_metadata.ingest_process;
create view macrostrat_api.map_ingest_tags as
    select * from maps_metadata.ingest_process_tag;

GRANT SELECT, UPDATE ON macrostrat_api.map_ingest TO web_user, web_admin;
GRANT SELECT, UPDATE ON macrostrat_api.map_ingest_tags TO web_user, web_admin;
NOTIFY pgrst, 'reload schema';
NOTIFY pgrst, 'reload schema';




