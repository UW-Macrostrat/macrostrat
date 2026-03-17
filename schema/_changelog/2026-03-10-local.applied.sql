
-- 2026-03-10 05:58:43
-- Environment: local
-- 15 changes applied (2 unsafe)
-- 12 statements were not logged

CREATE SEQUENCE "storage"."object_id_seq";
ALTER TABLE "macrostrat"."units" ALTER COLUMN "section_id" DROP DEFAULT;
ALTER TABLE "macrostrat"."units" ALTER COLUMN "section_id" DROP NOT NULL;

