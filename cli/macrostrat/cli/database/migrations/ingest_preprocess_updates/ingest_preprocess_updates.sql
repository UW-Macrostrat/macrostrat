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
GRANT SELECT, UPDATE ON maps_metadata.ingest_process TO web_user;
GRANT SELECT, UPDATE ON macrostrat_api.map_ingest_metadata TO web_user;

--add views for postgrest
create or replace view macrostrat_api.map_ingest as
    select * from maps_metadata.ingest_process;
create or replace view macrostrat_api.map_ingest_tags as
    select * from maps_metadata.ingest_process_tag;
create or replace view macrostrat_api.maps_sources AS
  select source_id,
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
         priority,
         display_scales,
         new_priority,
         status_code,
         slug,
         raster_url,
         scale_denominator,
         is_finalized,
         lines_oriented,
         date_finalized,
         ingested_by,
         keywords,
         language,
         description
  from maps.sources;



GRANT SELECT, UPDATE ON macrostrat_api.map_ingest TO web_user, web_admin;
GRANT SELECT, UPDATE ON macrostrat_api.map_ingest_tags TO web_user, web_admin;
GRANT SELECT, UPDATE ON macrostrat_api.maps_sources TO web_user, web_admin;

ALTER VIEW macrostrat_api.map_ingest OWNER TO web_admin;
ALTER VIEW macrostrat_api.map_ingest_tags OWNER TO web_admin;
ALTER VIEW macrostrat_api.maps_sources OWNER TO web_admin;

GRANT USAGE ON SCHEMA macrostrat_api TO web_anon;
GRANT SELECT ON macrostrat_api.map_ingest TO web_anon;
GRANT SELECT ON macrostrat_api.map_ingest_tags TO web_anon;
GRANT SELECT ON macrostrat_api.maps_sources TO web_anon;

NOTIFY pgrst, 'reload schema';




