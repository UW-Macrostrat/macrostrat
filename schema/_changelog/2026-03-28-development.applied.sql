
-- 2026-03-28 02:59:50
-- Environment: development
-- 96 changes applied (6 unsafe)
-- 73 statements were not logged

CREATE SCHEMA IF NOT EXISTS "tileserver_stats";
CREATE SEQUENCE "tileserver_stats"."requests_req_id_seq";
ALTER TABLE "macrostrat_xdd"."all_runs" DROP
CONSTRAINT "all_runs_root_id_fkey";
ALTER TABLE "macrostrat_xdd"."global_entity" DROP
CONSTRAINT "unique_entity";
ALTER TABLE "macrostrat"."strat_tree" DROP
CONSTRAINT "strat_tree_pkey";
ALTER TABLE "macrostrat_xdd"."global_entity" DROP
CONSTRAINT "global_entity_pkey";
CREATE TABLE "tileserver_stats"."day_index" ("layer" text NOT NULL, "ext" text NOT NULL, "referrer" text NOT NULL, "app" text NOT NULL, "app_version" text NOT NULL, "date" timestamp WITHOUT TIME ZONE NOT NULL, "num_requests" integer NOT NULL);
CREATE TABLE "tileserver_stats"."location_index" ("layer" text NOT NULL, "ext" text NOT NULL, "x" integer NOT NULL, "y" integer NOT NULL, "z" integer NOT NULL, "orig_z" integer NOT NULL, "num_requests" integer NOT NULL);
CREATE TABLE "tileserver_stats"."processing_status" ("last_row_id" integer NOT NULL, "last_row_time" timestamp WITHOUT TIME ZONE DEFAULT now());
CREATE TABLE "tileserver_stats"."requests" ("req_id" integer NOT NULL DEFAULT nextval('tileserver_stats.requests_req_id_seq'::regclass), "uri" text, "layer" text, "ext" text, "x" integer, "y" integer, "z" integer, "referrer" text, "app" text, "app_version" text, "cache_hit" boolean DEFAULT FALSE, "redis_hit" boolean DEFAULT FALSE, "time" timestamp WITHOUT TIME ZONE DEFAULT now());
ALTER TABLE "macrostrat"."cols" ALTER COLUMN "col_name"
   SET DATA TYPE CHARACTER varying(75) USING "col_name"::CHARACTER varying(75);
ALTER TABLE "macrostrat"."sections" ALTER COLUMN "fo_h"
   SET NOT NULL;
ALTER TABLE "macrostrat"."sections" ALTER COLUMN "lo_h"
   SET NOT NULL;
ALTER TABLE "macrostrat"."strat_name_footprints" ALTER COLUMN "rank_name"
   SET DATA TYPE CHARACTER varying(200) USING "rank_name"::CHARACTER varying(200);
ALTER TABLE "macrostrat_xdd"."all_runs" DROP COLUMN "root_id";
ALTER SEQUENCE "tileserver_stats"."requests_req_id_seq" owned BY "tileserver_stats"."requests"."req_id";
DROP SEQUENCE IF EXISTS "macrostrat_xdd"."global_entity_global_entity_id_seq";
CREATE UNIQUE INDEX day_index_layer_ext_referrer_app_app_version_date_key
    ON tileserver_stats.day_index USING btree (LAYER, ext, referrer, app, app_version, date);
CREATE UNIQUE INDEX location_index_layer_ext_x_y_z_orig_z_key
    ON tileserver_stats.location_index USING btree (LAYER, ext, x, y, z, orig_z);
CREATE UNIQUE INDEX requests_pkey
    ON tileserver_stats.requests USING btree (req_id);
ALTER TABLE "tileserver_stats"."requests" ADD
CONSTRAINT "requests_pkey" PRIMARY KEY USING INDEX "requests_pkey";
ALTER TABLE "tileserver_stats"."day_index" ADD
CONSTRAINT "day_index_layer_ext_referrer_app_app_version_date_key" UNIQUE USING INDEX "day_index_layer_ext_referrer_app_app_version_date_key";
ALTER TABLE "tileserver_stats"."location_index" ADD
CONSTRAINT "location_index_layer_ext_x_y_z_orig_z_key" UNIQUE USING INDEX "location_index_layer_ext_x_y_z_orig_z_key";

