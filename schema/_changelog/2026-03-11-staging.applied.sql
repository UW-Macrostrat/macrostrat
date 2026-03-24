
-- 2026-03-11 14:05:54
-- Environment: staging
-- 154 changes applied
-- 39 unsafe changes skipped
-- 49 statements were not logged

ALTER TABLE "macrostrat"."interval_boundaries" ALTER COLUMN "boundary_status"
   SET DEFAULT ''::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."interval_boundaries" ALTER COLUMN "boundary_status"
   SET DATA TYPE macrostrat.boundary_status USING "boundary_status"::text::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."interval_boundaries_scratch" ALTER COLUMN "boundary_status"
   SET DEFAULT ''::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."interval_boundaries_scratch" ALTER COLUMN "boundary_status"
   SET DATA TYPE macrostrat.boundary_status USING "boundary_status"::text::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "b_period"
   SET DEFAULT NULL::CHARACTER varying;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "bed_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "bed_name"
   SET DEFAULT NULL::CHARACTER varying;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "c_interval"
   SET DEFAULT NULL::CHARACTER varying;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "concept_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "early_age"
   SET DEFAULT NULL::numeric;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "fm_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "fm_name"
   SET DEFAULT NULL::CHARACTER varying;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "gp_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "gp_name"
   SET DEFAULT NULL::CHARACTER varying;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "gsc_lexicon"
   SET DEFAULT NULL::bpchar;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "late_age"
   SET DEFAULT NULL::numeric;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "mbr_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "mbr_name"
   SET DEFAULT NULL::CHARACTER varying;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "name_no_lith"
   SET DEFAULT NULL::CHARACTER varying;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "parent"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "rank_name"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "ref_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "sgp_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "sgp_name"
   SET DEFAULT NULL::CHARACTER varying;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "strat_name"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "subgp_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "subgp_name"
   SET DEFAULT NULL::CHARACTER varying;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "t_period"
   SET DEFAULT NULL::CHARACTER varying;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "t_units"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "tree"
   SET NOT NULL;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "burwell_polygons"
   SET DEFAULT '0'::bigint;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "burwell_polygons"
   SET DATA TYPE bigint USING "burwell_polygons"::bigint;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "columns"
   SET DEFAULT '0'::bigint;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "columns"
   SET NOT NULL;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "measurements"
   SET DEFAULT '0'::bigint;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "measurements"
   SET NOT NULL;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "packages"
   SET DEFAULT '0'::bigint;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "packages"
   SET NOT NULL;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "pbdb_collections"
   SET DEFAULT '0'::bigint;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "pbdb_collections"
   SET NOT NULL;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "project"
   SET NOT NULL;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "project"
   SET DATA TYPE macrostrat.stats_project USING "project"::macrostrat.stats_project;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "project_id"
   SET DEFAULT 0;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "project_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "units"
   SET DEFAULT '0'::bigint;
ALTER TABLE "macrostrat"."stats" ALTER COLUMN "units"
   SET NOT NULL;
ALTER TABLE "macrostrat"."strat_name_footprints" ALTER COLUMN "rank_name"
   SET DATA TYPE CHARACTER varying(200) USING "rank_name"::CHARACTER varying(200);
ALTER TABLE "macrostrat"."unit_boundaries" ALTER COLUMN "boundary_status"
   SET DEFAULT 'modeled'::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries" ALTER COLUMN "boundary_status"
   SET DATA TYPE macrostrat.boundary_status USING "boundary_status"::text::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries" ALTER COLUMN "boundary_type"
   SET DEFAULT ''::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries" ALTER COLUMN "boundary_type"
   SET DATA TYPE macrostrat.boundary_type USING "boundary_type"::text::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries_backup" ALTER COLUMN "boundary_status"
   SET DEFAULT 'modeled'::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries_backup" ALTER COLUMN "boundary_status"
   SET DATA TYPE macrostrat.boundary_status USING "boundary_status"::text::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries_backup" ALTER COLUMN "boundary_type"
   SET DEFAULT ''::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries_backup" ALTER COLUMN "boundary_type"
   SET DATA TYPE macrostrat.boundary_type USING "boundary_type"::text::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries_scratch" ALTER COLUMN "boundary_status"
   SET DEFAULT 'modeled'::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries_scratch" ALTER COLUMN "boundary_status"
   SET DATA TYPE macrostrat.boundary_status USING "boundary_status"::text::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries_scratch" ALTER COLUMN "boundary_type"
   SET DEFAULT ''::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries_scratch" ALTER COLUMN "boundary_type"
   SET DATA TYPE macrostrat.boundary_type USING "boundary_type"::text::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries_scratch_old" ALTER COLUMN "boundary_status"
   SET DEFAULT 'modeled'::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries_scratch_old" ALTER COLUMN "boundary_status"
   SET DATA TYPE macrostrat.boundary_status USING "boundary_status"::text::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries_scratch_old" ALTER COLUMN "boundary_type"
   SET DEFAULT ''::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries_scratch_old" ALTER COLUMN "boundary_type"
   SET DATA TYPE macrostrat.boundary_type USING "boundary_type"::text::macrostrat.boundary_type;
CREATE UNIQUE INDEX idx_44157014_primary
    ON macrostrat.cols USING btree (id);
CREATE UNIQUE INDEX idx_44157039_primary
    ON macrostrat.col_groups USING btree (id);
CREATE UNIQUE INDEX idx_44157059_primary
    ON macrostrat.econs USING btree (id);
CREATE UNIQUE INDEX idx_44157064_primary
    ON macrostrat.environs USING btree (id);
CREATE UNIQUE INDEX idx_44157069_primary
    ON macrostrat.intervals USING btree (id);
CREATE UNIQUE INDEX idx_44157091_primary
    ON macrostrat.liths USING btree (id);
CREATE UNIQUE INDEX idx_44157097_primary
    ON macrostrat.lith_atts USING btree (id);
CREATE UNIQUE INDEX idx_44157263_primary
    ON macrostrat.places USING btree (place_id);
CREATE UNIQUE INDEX idx_44157270_primary
    ON macrostrat.projects USING btree (id);
CREATE UNIQUE INDEX idx_44157277_primary
    ON macrostrat.refs USING btree (id);
CREATE UNIQUE INDEX idx_44157294_primary
    ON macrostrat.sections USING btree (id);
CREATE UNIQUE INDEX idx_44157311_primary
    ON macrostrat.strat_names USING btree (id);
CREATE UNIQUE INDEX idx_44157358_primary
    ON macrostrat.timescales USING btree (id);
CREATE UNIQUE INDEX idx_44157375_primary
    ON macrostrat.units USING btree (id);
CREATE UNIQUE INDEX idx_44157463_primary
    ON macrostrat.unit_liths USING btree (id);
ALTER TABLE "macrostrat"."col_groups" ADD
CONSTRAINT "idx_44157039_primary" PRIMARY KEY USING INDEX "idx_44157039_primary";
ALTER TABLE "macrostrat"."cols" ADD
CONSTRAINT "idx_44157014_primary" PRIMARY KEY USING INDEX "idx_44157014_primary";
ALTER TABLE "macrostrat"."econs" ADD
CONSTRAINT "idx_44157059_primary" PRIMARY KEY USING INDEX "idx_44157059_primary";
ALTER TABLE "macrostrat"."environs" ADD
CONSTRAINT "idx_44157064_primary" PRIMARY KEY USING INDEX "idx_44157064_primary";
ALTER TABLE "macrostrat"."intervals" ADD
CONSTRAINT "idx_44157069_primary" PRIMARY KEY USING INDEX "idx_44157069_primary";
ALTER TABLE "macrostrat"."lith_atts" ADD
CONSTRAINT "idx_44157097_primary" PRIMARY KEY USING INDEX "idx_44157097_primary";
ALTER TABLE "macrostrat"."liths" ADD
CONSTRAINT "idx_44157091_primary" PRIMARY KEY USING INDEX "idx_44157091_primary";
ALTER TABLE "macrostrat"."places" ADD
CONSTRAINT "idx_44157263_primary" PRIMARY KEY USING INDEX "idx_44157263_primary";
ALTER TABLE "macrostrat"."projects" ADD
CONSTRAINT "idx_44157270_primary" PRIMARY KEY USING INDEX "idx_44157270_primary";
ALTER TABLE "macrostrat"."refs" ADD
CONSTRAINT "idx_44157277_primary" PRIMARY KEY USING INDEX "idx_44157277_primary";
ALTER TABLE "macrostrat"."sections" ADD
CONSTRAINT "idx_44157294_primary" PRIMARY KEY USING INDEX "idx_44157294_primary";
ALTER TABLE "macrostrat"."strat_names" ADD
CONSTRAINT "idx_44157311_primary" PRIMARY KEY USING INDEX "idx_44157311_primary";
ALTER TABLE "macrostrat"."timescales" ADD
CONSTRAINT "idx_44157358_primary" PRIMARY KEY USING INDEX "idx_44157358_primary";
ALTER TABLE "macrostrat"."unit_liths" ADD
CONSTRAINT "idx_44157463_primary" PRIMARY KEY USING INDEX "idx_44157463_primary";
ALTER TABLE "macrostrat"."units" ADD
CONSTRAINT "idx_44157375_primary" PRIMARY KEY USING INDEX "idx_44157375_primary";
ALTER TABLE "macrostrat"."strat_names" ADD
CONSTRAINT "strat_names_strat_names_meta_fk"
FOREIGN KEY (concept_id) REFERENCES macrostrat.strat_names_meta(concept_id)
    ON DELETE CASCADE NOT VALID NOT VALID;
ALTER TABLE "macrostrat"."strat_names" VALIDATE
CONSTRAINT "strat_names_strat_names_meta_fk";
ALTER TABLE "maps"."lines" ADD
CONSTRAINT "maps_lines_geom_check" CHECK (maps.lines_geom_is_valid(geom)) NOT VALID;
ALTER TABLE "maps"."lines" VALIDATE
CONSTRAINT "maps_lines_geom_check";
ALTER TABLE "maps"."lines_large" ADD
CONSTRAINT "maps_lines_geom_check" CHECK (maps.lines_geom_is_valid(geom)) NOT VALID;
ALTER TABLE "maps"."lines_large" VALIDATE
CONSTRAINT "maps_lines_geom_check";
ALTER TABLE "maps"."lines_medium" ADD
CONSTRAINT "maps_lines_geom_check" CHECK (maps.lines_geom_is_valid(geom)) NOT VALID;
ALTER TABLE "maps"."lines_medium" VALIDATE
CONSTRAINT "maps_lines_geom_check";
ALTER TABLE "maps"."lines_small" ADD
CONSTRAINT "maps_lines_geom_check" CHECK (maps.lines_geom_is_valid(geom)) NOT VALID;
ALTER TABLE "maps"."lines_small" VALIDATE
CONSTRAINT "maps_lines_geom_check";
ALTER TABLE "maps"."lines_tiny" ADD
CONSTRAINT "maps_lines_geom_check" CHECK (maps.lines_geom_is_valid(geom)) NOT VALID;
ALTER TABLE "maps"."lines_tiny" VALIDATE
CONSTRAINT "maps_lines_geom_check";


-- 2026-03-11 15:24:38
-- Environment: staging
-- 145 changes applied (36 unsafe)
-- 44 statements were not logged

ALTER TABLE "macrostrat"."unit_boundaries" DROP
CONSTRAINT "unit_boundaries_ref_id_fkey1";
ALTER TABLE "macrostrat"."unit_boundaries" DROP
CONSTRAINT "unit_boundaries_unit_id_fkey1";
ALTER TABLE "maps"."polygons_large" DROP
CONSTRAINT "maps_polygons_large_source_id_fkey";
ALTER TABLE "maps"."polygons_medium" DROP
CONSTRAINT "maps_polygons_medium_source_id_fkey";
ALTER TABLE "maps"."polygons_small" DROP
CONSTRAINT "maps_polygons_small_source_id_fkey";
ALTER TABLE "maps"."polygons_tiny" DROP
CONSTRAINT "maps_polygons_tiny_source_id_fkey";
ALTER TABLE "macrostrat"."strat_names" DROP
CONSTRAINT "strat_names_strat_names_meta_fk";
ALTER TABLE "maps"."lines" DROP
CONSTRAINT "maps_lines_geom_check";
ALTER TABLE "maps"."lines_large" DROP
CONSTRAINT "maps_lines_geom_check";
ALTER TABLE "macrostrat"."col_groups" DROP
CONSTRAINT "idx_81799123_primary";
ALTER TABLE "macrostrat"."cols" DROP
CONSTRAINT "idx_81799098_primary";
ALTER TABLE "macrostrat"."econs" DROP
CONSTRAINT "idx_81799143_primary";
ALTER TABLE "macrostrat"."environs" DROP
CONSTRAINT "idx_81799148_primary";
ALTER TABLE "macrostrat"."intervals" DROP
CONSTRAINT "idx_81799153_primary";
ALTER TABLE "macrostrat"."lith_atts" DROP
CONSTRAINT "idx_81799181_primary";
ALTER TABLE "macrostrat"."liths" DROP
CONSTRAINT "idx_81799175_primary";
ALTER TABLE "macrostrat"."places" DROP
CONSTRAINT "idx_81799347_primary";
ALTER TABLE "macrostrat"."projects" DROP
CONSTRAINT "idx_81799354_primary";
ALTER TABLE "macrostrat"."refs" DROP
CONSTRAINT "idx_81799361_primary";
ALTER TABLE "macrostrat"."sections" DROP
CONSTRAINT "idx_81799378_primary";
ALTER TABLE "macrostrat"."strat_names" DROP
CONSTRAINT "idx_81799395_primary";
ALTER TABLE "macrostrat"."timescales" DROP
CONSTRAINT "idx_81799442_primary";
ALTER TABLE "macrostrat"."unit_liths" DROP
CONSTRAINT "idx_81799547_primary";
ALTER TABLE "macrostrat"."units" DROP
CONSTRAINT "idx_81799459_primary";
DROP TABLE "macrostrat"."lookup_strat_names_old";
DROP TABLE "macrostrat".strat_name_footprints;
ALTER TABLE "macrostrat"."interval_boundaries" ALTER COLUMN "boundary_status"
   SET DEFAULT ''::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."interval_boundaries" ALTER COLUMN "boundary_status"
   SET DATA TYPE macrostrat.boundary_status USING "boundary_status"::text::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."interval_boundaries_scratch" ALTER COLUMN "boundary_status"
   SET DEFAULT ''::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."interval_boundaries_scratch" ALTER COLUMN "boundary_status"
   SET DATA TYPE macrostrat.boundary_status USING "boundary_status"::text::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "bed_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "concept_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "fm_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "gp_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "mbr_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "ref_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "sgp_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "subgp_id"
   SET NOT NULL;
ALTER TABLE "macrostrat"."lookup_strat_names" ALTER COLUMN "t_units"
   SET NOT NULL;
ALTER TABLE "macrostrat"."unit_boundaries" ALTER COLUMN "boundary_status"
   SET DEFAULT 'modeled'::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries" ALTER COLUMN "boundary_status"
   SET DATA TYPE macrostrat.boundary_status USING "boundary_status"::text::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries" ALTER COLUMN "boundary_type"
   SET DEFAULT ''::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries" ALTER COLUMN "boundary_type"
   SET DATA TYPE macrostrat.boundary_type USING "boundary_type"::text::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries_backup" ALTER COLUMN "boundary_status"
   SET DEFAULT 'modeled'::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries_backup" ALTER COLUMN "boundary_status"
   SET DATA TYPE macrostrat.boundary_status USING "boundary_status"::text::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries_backup" ALTER COLUMN "boundary_type"
   SET DEFAULT ''::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries_backup" ALTER COLUMN "boundary_type"
   SET DATA TYPE macrostrat.boundary_type USING "boundary_type"::text::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries_scratch" ALTER COLUMN "boundary_status"
   SET DEFAULT 'modeled'::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries_scratch" ALTER COLUMN "boundary_status"
   SET DATA TYPE macrostrat.boundary_status USING "boundary_status"::text::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries_scratch" ALTER COLUMN "boundary_type"
   SET DEFAULT ''::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries_scratch" ALTER COLUMN "boundary_type"
   SET DATA TYPE macrostrat.boundary_type USING "boundary_type"::text::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries_scratch_old" ALTER COLUMN "boundary_status"
   SET DEFAULT 'modeled'::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries_scratch_old" ALTER COLUMN "boundary_status"
   SET DATA TYPE macrostrat.boundary_status USING "boundary_status"::text::macrostrat.boundary_status;
ALTER TABLE "macrostrat"."unit_boundaries_scratch_old" ALTER COLUMN "boundary_type"
   SET DEFAULT ''::macrostrat.boundary_type;
ALTER TABLE "macrostrat"."unit_boundaries_scratch_old" ALTER COLUMN "boundary_type"
   SET DATA TYPE macrostrat.boundary_type USING "boundary_type"::text::macrostrat.boundary_type;
DROP TYPE "macrostrat"."interval_boundaries_boundary_status";
DROP TYPE "macrostrat"."interval_boundaries_scratch_boundary_status";
DROP TYPE "macrostrat"."unit_boundaries_backup_boundary_status";
DROP TYPE "macrostrat"."unit_boundaries_backup_boundary_type";
DROP TYPE "macrostrat"."unit_boundaries_boundary_status";
DROP TYPE "macrostrat"."unit_boundaries_boundary_type";
DROP TYPE "macrostrat"."unit_boundaries_scratch_boundary_status";
DROP TYPE "macrostrat"."unit_boundaries_scratch_boundary_type";
DROP TYPE "macrostrat"."unit_boundaries_scratch_old_boundary_status";
DROP TYPE "macrostrat"."unit_boundaries_scratch_old_boundary_type";
CREATE UNIQUE INDEX idx_44157014_primary
    ON macrostrat.cols USING btree (id);
CREATE UNIQUE INDEX idx_44157039_primary
    ON macrostrat.col_groups USING btree (id);
CREATE UNIQUE INDEX idx_44157059_primary
    ON macrostrat.econs USING btree (id);
CREATE UNIQUE INDEX idx_44157064_primary
    ON macrostrat.environs USING btree (id);
CREATE UNIQUE INDEX idx_44157069_primary
    ON macrostrat.intervals USING btree (id);
CREATE UNIQUE INDEX idx_44157091_primary
    ON macrostrat.liths USING btree (id);
CREATE UNIQUE INDEX idx_44157097_primary
    ON macrostrat.lith_atts USING btree (id);
CREATE UNIQUE INDEX idx_44157263_primary
    ON macrostrat.places USING btree (place_id);
CREATE UNIQUE INDEX idx_44157270_primary
    ON macrostrat.projects USING btree (id);
CREATE UNIQUE INDEX idx_44157277_primary
    ON macrostrat.refs USING btree (id);
CREATE UNIQUE INDEX idx_44157294_primary
    ON macrostrat.sections USING btree (id);
CREATE UNIQUE INDEX idx_44157311_primary
    ON macrostrat.strat_names USING btree (id);
CREATE UNIQUE INDEX idx_44157358_primary
    ON macrostrat.timescales USING btree (id);
CREATE UNIQUE INDEX idx_44157375_primary
    ON macrostrat.units USING btree (id);
CREATE UNIQUE INDEX idx_44157463_primary
    ON macrostrat.unit_liths USING btree (id);
ALTER TABLE "macrostrat"."col_groups" ADD
CONSTRAINT "idx_44157039_primary" PRIMARY KEY USING INDEX "idx_44157039_primary";
ALTER TABLE "macrostrat"."cols" ADD
CONSTRAINT "idx_44157014_primary" PRIMARY KEY USING INDEX "idx_44157014_primary";
ALTER TABLE "macrostrat"."econs" ADD
CONSTRAINT "idx_44157059_primary" PRIMARY KEY USING INDEX "idx_44157059_primary";
ALTER TABLE "macrostrat"."environs" ADD
CONSTRAINT "idx_44157064_primary" PRIMARY KEY USING INDEX "idx_44157064_primary";
ALTER TABLE "macrostrat"."intervals" ADD
CONSTRAINT "idx_44157069_primary" PRIMARY KEY USING INDEX "idx_44157069_primary";
ALTER TABLE "macrostrat"."lith_atts" ADD
CONSTRAINT "idx_44157097_primary" PRIMARY KEY USING INDEX "idx_44157097_primary";
ALTER TABLE "macrostrat"."liths" ADD
CONSTRAINT "idx_44157091_primary" PRIMARY KEY USING INDEX "idx_44157091_primary";
ALTER TABLE "macrostrat"."places" ADD
CONSTRAINT "idx_44157263_primary" PRIMARY KEY USING INDEX "idx_44157263_primary";
ALTER TABLE "macrostrat"."projects" ADD
CONSTRAINT "idx_44157270_primary" PRIMARY KEY USING INDEX "idx_44157270_primary";
ALTER TABLE "macrostrat"."refs" ADD
CONSTRAINT "idx_44157277_primary" PRIMARY KEY USING INDEX "idx_44157277_primary";
ALTER TABLE "macrostrat"."sections" ADD
CONSTRAINT "idx_44157294_primary" PRIMARY KEY USING INDEX "idx_44157294_primary";
ALTER TABLE "macrostrat"."strat_names" ADD
CONSTRAINT "idx_44157311_primary" PRIMARY KEY USING INDEX "idx_44157311_primary";
ALTER TABLE "macrostrat"."timescales" ADD
CONSTRAINT "idx_44157358_primary" PRIMARY KEY USING INDEX "idx_44157358_primary";
ALTER TABLE "macrostrat"."unit_liths" ADD
CONSTRAINT "idx_44157463_primary" PRIMARY KEY USING INDEX "idx_44157463_primary";
ALTER TABLE "macrostrat"."units" ADD
CONSTRAINT "idx_44157375_primary" PRIMARY KEY USING INDEX "idx_44157375_primary";
ALTER TABLE "macrostrat"."strat_names" ADD
CONSTRAINT "strat_names_strat_names_meta_fk"
FOREIGN KEY (concept_id) REFERENCES macrostrat.strat_names_meta(concept_id)
    ON DELETE CASCADE NOT VALID;
ALTER TABLE "macrostrat"."strat_names" VALIDATE
CONSTRAINT "strat_names_strat_names_meta_fk";
ALTER TABLE "maps"."lines" ADD
CONSTRAINT "maps_lines_geom_check" CHECK (maps.lines_geom_is_valid(geom)) NOT VALID;
ALTER TABLE "maps"."lines" VALIDATE
CONSTRAINT "maps_lines_geom_check";
ALTER TABLE "maps"."lines_large" ADD
CONSTRAINT "maps_lines_geom_check" CHECK (maps.lines_geom_is_valid(geom)) NOT VALID;
ALTER TABLE "maps"."lines_large" VALIDATE
CONSTRAINT "maps_lines_geom_check";

