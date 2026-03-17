
-- 2026-03-09 20:40:01
-- Environment: local
-- 126 changes applied (24 unsafe)
-- 76 statements were not logged

ALTER TABLE "macrostrat"."unit_boundaries" DROP
CONSTRAINT "unit_boundaries_ref_id_fkey1";
ALTER TABLE "macrostrat"."unit_boundaries" DROP
CONSTRAINT "unit_boundaries_ref_id_fkey2";
ALTER TABLE "macrostrat"."unit_boundaries" DROP
CONSTRAINT "unit_boundaries_ref_id_fkey3";
ALTER TABLE "macrostrat"."unit_boundaries" DROP
CONSTRAINT "unit_boundaries_ref_id_fkey4";
ALTER TABLE "macrostrat"."unit_boundaries" DROP
CONSTRAINT "unit_boundaries_unit_id_fkey1";
ALTER TABLE "macrostrat"."unit_boundaries" DROP
CONSTRAINT "unit_boundaries_unit_id_fkey2";
ALTER TABLE "macrostrat"."unit_boundaries" DROP
CONSTRAINT "unit_boundaries_unit_id_fkey3";
ALTER TABLE "macrostrat"."unit_boundaries" DROP
CONSTRAINT "unit_boundaries_unit_id_fkey4";
ALTER TABLE "maps_metadata"."map_files" DROP
CONSTRAINT "map_files_object_id_fkey";
ALTER TABLE "storage"."object" DROP
CONSTRAINT "unique_file";
ALTER TABLE "storage"."object" DROP
CONSTRAINT "object_pkey";
DROP TABLE "macrostrat"."lookup_unit_intervals_new";
DROP TABLE "storage"."object";
CREATE TABLE "storage"."objects" ("id" integer NOT NULL, "scheme" storage.scheme NOT NULL, "host" CHARACTER varying(255) NOT NULL, "bucket" CHARACTER varying(255) NOT NULL, "key" CHARACTER varying(255) NOT NULL, "source" JSONB, "mime_type" CHARACTER varying(255), "sha256_hash" CHARACTER varying(255), "created_on" timestamp WITH TIME ZONE NOT NULL DEFAULT now(), "updated_on" timestamp WITH TIME ZONE NOT NULL DEFAULT now(), "deleted_on" timestamp WITH TIME ZONE);
ALTER TABLE "macrostrat"."cols" ALTER COLUMN "col_name"
   SET DATA TYPE text USING "col_name"::text;
ALTER TABLE "macrostrat"."sections" ALTER COLUMN "fo_h" DROP NOT NULL;
ALTER TABLE "macrostrat"."sections" ALTER COLUMN "lo_h" DROP NOT NULL;
ALTER TABLE "macrostrat"."strat_names" ALTER COLUMN "old_id" DROP NOT NULL;
ALTER TABLE "macrostrat"."strat_names" ALTER COLUMN "old_strat_name_id" DROP NOT NULL;
ALTER TABLE "macrostrat"."strat_names" ALTER COLUMN "orig_id" DROP NOT NULL;
ALTER TABLE "macrostrat"."strat_tree" ALTER COLUMN "id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."strat_tree" ALTER COLUMN "id" ADD GENERATED always AS IDENTITY;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "fo_h" DROP DEFAULT;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "fo_h" DROP NOT NULL;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "lo_h" DROP DEFAULT;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "lo_h" DROP NOT NULL;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "max_thick" DROP NOT NULL;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "min_thick" DROP NOT NULL;
ALTER TABLE "macrostrat_gbdb"."sections" ALTER COLUMN "section_id"
   SET NOT NULL;
ALTER TABLE "macrostrat_gbdb"."summary_columns" ALTER COLUMN "geometry"
   SET DATA TYPE geometry(POLYGON,4326) USING "geometry"::geometry(POLYGON,4326);
ALTER TABLE "macrostrat_gbdb"."summary_columns" ALTER COLUMN "id"
   SET NOT NULL;
ALTER TABLE "macrostrat_gbdb"."summary_columns" ALTER COLUMN "id"
   SET DATA TYPE integer USING "id"::integer;
ALTER TABLE "macrostrat_gbdb"."summary_units" ALTER COLUMN "col_id"
   SET DATA TYPE integer USING "col_id"::integer;
ALTER TABLE "macrostrat_gbdb"."summary_units" ALTER COLUMN "unit_id"
   SET NOT NULL;
ALTER TABLE "macrostrat_gbdb"."summary_units" ALTER COLUMN "unit_id"
   SET DATA TYPE integer USING "unit_id"::integer;
ALTER SEQUENCE "storage"."object_id_seq" owned BY
  NONE;
CREATE UNIQUE INDEX idx_44157129_primary
    ON macrostrat.lookup_units USING btree (unit_id);
CREATE UNIQUE INDEX strat_tree_pkey
    ON macrostrat.strat_tree USING btree (id);
CREATE UNIQUE INDEX sections_pkey
    ON macrostrat_gbdb.sections USING btree (section_id);
CREATE UNIQUE INDEX summary_columns_pkey
    ON macrostrat_gbdb.summary_columns USING btree (id);
CREATE UNIQUE INDEX summary_units_pkey
    ON macrostrat_gbdb.summary_units USING btree (unit_id);
CREATE UNIQUE INDEX object_pkey
    ON storage.objects USING btree (id);
CREATE UNIQUE INDEX unique_file
    ON storage.objects USING btree (scheme, HOST, bucket, KEY);
ALTER TABLE "macrostrat"."lookup_units" ADD
CONSTRAINT "idx_44157129_primary" PRIMARY KEY USING INDEX "idx_44157129_primary";
ALTER TABLE "macrostrat"."strat_tree" ADD
CONSTRAINT "strat_tree_pkey" PRIMARY KEY USING INDEX "strat_tree_pkey";
ALTER TABLE "macrostrat_gbdb"."sections" ADD
CONSTRAINT "sections_pkey" PRIMARY KEY USING INDEX "sections_pkey";
ALTER TABLE "macrostrat_gbdb"."summary_columns" ADD
CONSTRAINT "summary_columns_pkey" PRIMARY KEY USING INDEX "summary_columns_pkey";
ALTER TABLE "macrostrat_gbdb"."summary_units" ADD
CONSTRAINT "summary_units_pkey" PRIMARY KEY USING INDEX "summary_units_pkey";
ALTER TABLE "storage"."objects" ADD
CONSTRAINT "object_pkey" PRIMARY KEY USING INDEX "object_pkey";
ALTER TABLE "storage"."objects" ADD
CONSTRAINT "unique_file" UNIQUE USING INDEX "unique_file";

