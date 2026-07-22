CREATE SCHEMA IF NOT EXISTS macrostrat_api;

CREATE OR REPLACE VIEW macrostrat_api.map_ingest_metadata AS
SELECT * FROM maps_metadata.ingest_process;

GRANT SELECT, UPDATE ON maps_metadata.ingest_process TO web_user;
GRANT SELECT, UPDATE ON macrostrat_api.map_ingest_metadata TO web_user;

--add views for postgrest
CREATE OR REPLACE VIEW macrostrat_api.map_ingest AS
SELECT * FROM maps_metadata.ingest_process;

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


GRANT USAGE ON SCHEMA macrostrat_api TO web_anon;
GRANT SELECT ON macrostrat_api.map_ingest TO web_anon;
GRANT SELECT ON macrostrat_api.map_ingest_tags TO web_anon;
GRANT SELECT ON macrostrat_api.maps_sources TO web_anon;



