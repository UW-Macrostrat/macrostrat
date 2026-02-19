
-- 2026-01-05 12:46:44
-- Environment: development
-- 112 changes applied
-- 92 statements were not logged

CREATE UNIQUE INDEX col_refs_unique
    ON macrostrat.col_refs USING btree (col_id, ref_id);
ALTER TABLE "macrostrat"."col_groups" ADD
CONSTRAINT "col_groups_project_fk"
FOREIGN KEY (project_id) REFERENCES macrostrat.projects(id)
    ON UPDATE CASCADE NOT VALID;
ALTER TABLE "macrostrat"."col_refs" ADD
CONSTRAINT "col_refs_unique" UNIQUE USING INDEX "col_refs_unique";
ALTER TABLE "macrostrat"."concepts_places" ADD
CONSTRAINT "concepts_places_concepts_fk"
FOREIGN KEY (concept_id) REFERENCES macrostrat.strat_names_meta(concept_id)
    ON DELETE CASCADE NOT VALID;
ALTER TABLE "macrostrat"."concepts_places" VALIDATE
CONSTRAINT "concepts_places_concepts_fk";
ALTER TABLE "macrostrat"."strat_names_meta" ADD
CONSTRAINT "strat_names_meta_b_int_fk"
FOREIGN KEY (b_int) REFERENCES macrostrat.intervals(id) NOT VALID;
ALTER TABLE "macrostrat"."strat_names_meta" ADD
CONSTRAINT "strat_names_meta_t_int_fk"
FOREIGN KEY (t_int) REFERENCES macrostrat.intervals(id) NOT VALID;
ALTER TABLE "macrostrat"."strat_names_meta" VALIDATE
CONSTRAINT "strat_names_meta_t_int_fk";
ALTER TABLE "macrostrat"."strat_tree" ADD
CONSTRAINT "strat_tree_refs_fk"
FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) NOT VALID;
ALTER TABLE "macrostrat"."strat_tree" VALIDATE
CONSTRAINT "strat_tree_refs_fk";
ALTER TABLE "macrostrat"."strat_tree" ADD
CONSTRAINT "strat_tree_strat_names_child_fk"
FOREIGN KEY (child) REFERENCES macrostrat.strat_names(id)
    ON DELETE CASCADE NOT VALID;
ALTER TABLE "macrostrat"."strat_tree" VALIDATE
CONSTRAINT "strat_tree_strat_names_child_fk";
ALTER TABLE "macrostrat"."strat_tree" ADD
CONSTRAINT "strat_tree_strat_names_parent_fk"
FOREIGN KEY (parent) REFERENCES macrostrat.strat_names(id)
    ON DELETE CASCADE NOT VALID;
ALTER TABLE "macrostrat"."strat_tree" VALIDATE
CONSTRAINT "strat_tree_strat_names_parent_fk";
ALTER TABLE "macrostrat"."unit_boundaries" ADD
CONSTRAINT "unit_boundaries_ref_id_fkey"
FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id)
    ON DELETE CASCADE NOT VALID;
ALTER TABLE "macrostrat"."unit_boundaries" VALIDATE
CONSTRAINT "unit_boundaries_ref_id_fkey";
ALTER TABLE "macrostrat"."unit_boundaries" ADD
CONSTRAINT "unit_boundaries_unit_id_fkey"
FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id)
    ON DELETE CASCADE NOT VALID;
ALTER TABLE "macrostrat"."unit_boundaries" VALIDATE
CONSTRAINT "unit_boundaries_unit_id_fkey";
ALTER TABLE "macrostrat"."units_sections" ADD
CONSTRAINT "units_sections_cols_fk"
FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id)
    ON DELETE CASCADE NOT VALID;
ALTER TABLE "macrostrat"."units_sections" VALIDATE
CONSTRAINT "units_sections_cols_fk";


-- 2026-01-05 14:21:57
-- Environment: development
-- 28 changes applied
-- 22 statements were not logged

ALTER TABLE "macrostrat"."strat_names" ADD
CONSTRAINT "strat_names_strat_names_meta_fk"
FOREIGN KEY (concept_id) REFERENCES macrostrat.strat_names_meta(concept_id)
    ON DELETE CASCADE NOT VALID;
ALTER TABLE "macrostrat"."strat_names" VALIDATE
CONSTRAINT "strat_names_strat_names_meta_fk";
ALTER TABLE "macrostrat"."strat_names_meta" ADD
CONSTRAINT "strat_names_meta_interval_fk"
FOREIGN KEY (interval_id) REFERENCES macrostrat.intervals(id) NOT VALID;
ALTER TABLE "macrostrat"."strat_names_meta" VALIDATE
CONSTRAINT "strat_names_meta_interval_fk";
ALTER TABLE "macrostrat"."strat_names_meta" ADD
CONSTRAINT "strat_names_meta_refs_fk"
FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) NOT VALID;
ALTER TABLE "macrostrat"."strat_names_meta" VALIDATE
CONSTRAINT "strat_names_meta_refs_fk";

