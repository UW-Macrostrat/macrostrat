
-- 2026-07-08 03:38:18
-- Environment: local
-- 37 changes applied (15 unsafe)
-- 8 statements were not logged

DROP TRIGGER IF EXISTS "maps_metadata_update_trigger"
    ON "maps_metadata"."sources_meta";
ALTER TABLE "maps_metadata"."map_files" DROP
CONSTRAINT "unique_ingest_object";
ALTER TABLE "map_bounds"."map_area" DROP
CONSTRAINT "check_topogeom_topo";
ALTER TABLE "map_bounds"."map_topo" DROP
CONSTRAINT "check_topogeom_topo";
ALTER TABLE "map_bounds_topology"."map_face" DROP
CONSTRAINT "check_topogeom_topo";
ALTER TABLE "maps_metadata"."ingest_process" DROP
CONSTRAINT "ingest_process_state_fkey";
DROP
FUNCTION IF EXISTS "map_ingestion_api"."aggregate_if_small"(state anyarray);
DROP
FUNCTION IF EXISTS "map_ingestion_api"."collect_unique_values"(state text[], next_val anyelement);
DROP
FUNCTION IF EXISTS "public"."aggregate_if_small"(state anyarray);
DROP
FUNCTION IF EXISTS "public"."collect_unique_values"(state anyarray, next_val anyelement);
CREATE TABLE "maps_metadata"."ingest_result" ("id" integer GENERATED always AS IDENTITY NOT NULL, "source_id" integer NOT NULL, "description" text, "error" text, "processing_step" text, "date" timestamp WITH TIME ZONE NOT NULL DEFAULT now(), "details" JSONB);
ALTER TABLE "maps_metadata"."ingest_process" DROP COLUMN "map_id";
ALTER TABLE "maps_metadata"."ingest_process" DROP COLUMN "map_url";
ALTER TABLE "maps_metadata"."ingest_process" DROP COLUMN "type";
ALTER TABLE "maps_metadata"."ingest_process" ALTER COLUMN "id" DROP DEFAULT;
ALTER TABLE "maps_metadata"."ingest_process" ALTER COLUMN "id" ADD GENERATED always AS IDENTITY;
ALTER TABLE "maps_metadata"."ingest_process" ALTER COLUMN "source_id"
   SET NOT NULL;
DROP SEQUENCE IF EXISTS "maps_metadata"."ingest_process_id_seq";
DROP TYPE "maps"."ingest_type";
CREATE UNIQUE INDEX ingest_process_source_id_unique
    ON maps_metadata.ingest_process USING btree (source_id);
CREATE UNIQUE INDEX ingest_result_pkey
    ON maps_metadata.ingest_result USING btree (id);
ALTER TABLE "maps_metadata"."ingest_result" ADD
CONSTRAINT "ingest_result_pkey" PRIMARY KEY USING INDEX "ingest_result_pkey";
ALTER TABLE "maps_metadata"."ingest_process" ADD
CONSTRAINT "ingest_process_source_id_unique" UNIQUE USING INDEX "ingest_process_source_id_unique";
ALTER TABLE "maps_metadata"."ingest_result" ADD
CONSTRAINT "ingest_result_source_id_fkey"
FOREIGN KEY (source_id) REFERENCES maps.sources(source_id) NOT VALID;
ALTER TABLE "maps_metadata"."ingest_result" VALIDATE
CONSTRAINT "ingest_result_source_id_fkey";
ALTER TABLE "maps_metadata"."ingest_process" ADD
CONSTRAINT "ingest_process_state_fkey"
FOREIGN KEY (state) REFERENCES maps_metadata.ingest_state(id) NOT VALID;
ALTER TABLE "maps_metadata"."ingest_process" VALIDATE
CONSTRAINT "ingest_process_state_fkey";
CREATE OR REPLACE
FUNCTION maps_metadata.maps_metadata_update_trigger() RETURNS TRIGGER LANGUAGE PLPGSQL AS $function$
BEGIN
  UPDATE
    sources
  SET
    raster_source_url = NEW.raster_source_url,
    raster_bucket_url = NEW.raster_bucket_url,
    compiler_name = NEW.compiler_name,
    date_compiled = NEW.date_compiled
  WHERE source_id = NEW.source_id;
  RETURN NEW;
END;
$function$ ;
CREATE TRIGGER maps_metadata_update_trigger INSTEAD OF UPDATE
    ON maps_metadata.sources_meta
   FOR EACH ROW EXECUTE
FUNCTION maps_metadata.maps_metadata_update_trigger()

