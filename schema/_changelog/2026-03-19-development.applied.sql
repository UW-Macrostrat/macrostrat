
-- 2026-03-19 06:06:31
-- Environment: development
-- 107 changes applied (22 unsafe)
-- 77 statements were not logged

ALTER TABLE "integrations"."geomag_sites" DROP
CONSTRAINT "geomag_sites_external_site_key";
ALTER TABLE "integrations"."geomag_units" DROP
CONSTRAINT "geomag_units_geomag_site_id_fkey";
ALTER TABLE "macrostrat"."strat_names" DROP
CONSTRAINT "strat_names_strat_names_meta_fk";
ALTER TABLE "integrations"."geomag_sites" DROP
CONSTRAINT "geomag_sites_pkey";
ALTER TABLE "integrations"."geomag_units" DROP
CONSTRAINT "geomag_units_pkey";
DROP TABLE "integrations"."geomag_sites";
DROP TABLE "integrations"."geomag_units";
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
ALTER TABLE "macrostrat"."unit_boundaries" ALTER COLUMN "unit_id" DROP NOT NULL;
ALTER TABLE "macrostrat"."unit_boundaries" ALTER COLUMN "unit_id_2" DROP NOT NULL;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "fo_h" DROP DEFAULT;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "fo_h" DROP NOT NULL;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "lo_h" DROP DEFAULT;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "lo_h" DROP NOT NULL;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "max_thick" DROP NOT NULL;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "min_thick" DROP NOT NULL;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "section_id" DROP DEFAULT;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "section_id" DROP NOT NULL;
CREATE UNIQUE INDEX strat_tree_pkey
    ON macrostrat.strat_tree USING btree (id);
ALTER TABLE "macrostrat"."strat_tree" ADD
CONSTRAINT "strat_tree_pkey" PRIMARY KEY USING INDEX "strat_tree_pkey";
ALTER TABLE "macrostrat"."unit_boundaries" ADD
CONSTRAINT "unit_boundaries_check" CHECK (((unit_id IS NOT NULL) OR (unit_id_2 IS NOT NULL))) NOT VALID;
ALTER TABLE "macrostrat"."unit_boundaries" VALIDATE
CONSTRAINT "unit_boundaries_check";
ALTER TABLE "macrostrat"."strat_names" ADD
CONSTRAINT "strat_names_strat_names_meta_fk"
FOREIGN KEY (concept_id) REFERENCES macrostrat.strat_names_meta(concept_id)
    ON DELETE CASCADE NOT VALID;

