
-- 2026-03-31 11:48:18
-- Environment: local
-- 39 changes applied (6 unsafe)
-- 25 statements were not logged

ALTER TABLE "macrostrat"."strat_tree" DROP
CONSTRAINT "strat_tree_pkey";
ALTER TABLE "public"."impervious" DROP
CONSTRAINT "impervious_pkey";
DROP TABLE "public"."impervious";
ALTER TABLE "macrostrat"."cols" ALTER COLUMN "col_name"
   SET DATA TYPE CHARACTER varying(75) USING "col_name"::CHARACTER varying(75);
ALTER TABLE "macrostrat"."sections" ALTER COLUMN "fo_h"
   SET NOT NULL;
ALTER TABLE "macrostrat"."sections" ALTER COLUMN "lo_h"
   SET NOT NULL;
ALTER TABLE "macrostrat"."strat_names" ALTER COLUMN "old_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."strat_names" ALTER COLUMN "old_strat_name_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."strat_names" ALTER COLUMN "orig_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."strat_tree" ALTER COLUMN "id" DROP IDENTITY;
ALTER TABLE "macrostrat"."strat_tree" ALTER COLUMN "id" DROP NOT NULL;
ALTER TABLE "macrostrat"."unit_boundaries" ALTER COLUMN "unit_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."unit_boundaries" ALTER COLUMN "unit_id_2"
   SET NOT NULL;
DROP SEQUENCE IF EXISTS "public"."impervious_rid_seq";

