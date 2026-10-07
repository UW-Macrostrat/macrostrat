CREATE SCHEMA IF NOT EXISTS macrostrat_api;

-- Reading the ingestion queue is open; changing it is an administrator's
-- job. A signed-in user (web_user) is anyone with an ORCID iD, so writes are
-- never granted to that tier.
GRANT SELECT ON maps_metadata.ingest_process TO web_user;
GRANT UPDATE ON maps_metadata.ingest_process TO web_admin;

-- removed duplicate map_ingest_metadata
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



GRANT SELECT ON macrostrat_api.map_ingest TO web_user;
GRANT SELECT ON macrostrat_api.map_ingest_tags TO web_user;
GRANT SELECT ON macrostrat_api.maps_sources TO web_user;
GRANT UPDATE ON macrostrat_api.map_ingest TO web_admin;
GRANT UPDATE ON macrostrat_api.map_ingest_tags TO web_admin;
GRANT UPDATE ON macrostrat_api.maps_sources TO web_admin;


GRANT USAGE ON SCHEMA macrostrat_api TO web_anon;
GRANT SELECT ON macrostrat_api.map_ingest TO web_anon;
GRANT SELECT ON macrostrat_api.map_ingest_tags TO web_anon;
GRANT SELECT ON macrostrat_api.maps_sources TO web_anon;
GRANT INSERT, DELETE ON macrostrat_api.map_ingest_tags TO web_admin;


