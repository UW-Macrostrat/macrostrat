
-- 2026-01-05 11:13:19
-- Environment: local
-- 18 changes applied (2 unsafe)

ALTER TABLE "macrostrat"."strat_names_meta" DROP
CONSTRAINT "strat_names_meta_intervals_fk";
ALTER TABLE "macrostrat"."strat_names_meta" DROP
CONSTRAINT "strat_names_meta_refs_fk";
CREATE UNIQUE INDEX col_refs_unique
    ON macrostrat.col_refs USING btree (col_id, ref_id);
ALTER TABLE "macrostrat"."col_refs" ADD
CONSTRAINT "col_refs_unique" UNIQUE USING INDEX "col_refs_unique";
ALTER TABLE "macrostrat"."strat_names_meta" ADD
CONSTRAINT "strat_names_meta_b_int_fk"
FOREIGN KEY (b_int) REFERENCES macrostrat.intervals(id) NOT VALID;
ALTER TABLE "macrostrat"."strat_names_meta" VALIDATE
CONSTRAINT "strat_names_meta_b_int_fk";
ALTER TABLE "macrostrat"."strat_names_meta" ADD
CONSTRAINT "strat_names_meta_interval_fk"
FOREIGN KEY (interval_id) REFERENCES macrostrat.intervals(id) NOT VALID;
ALTER TABLE "macrostrat"."strat_names_meta" VALIDATE
CONSTRAINT "strat_names_meta_interval_fk";
ALTER TABLE "macrostrat"."strat_names_meta" ADD
CONSTRAINT "strat_names_meta_t_int_fk"
FOREIGN KEY (t_int) REFERENCES macrostrat.intervals(id) NOT VALID;
ALTER TABLE "macrostrat"."strat_names_meta" VALIDATE
CONSTRAINT "strat_names_meta_t_int_fk";
ALTER TABLE "macrostrat"."strat_tree" ADD
CONSTRAINT "strat_tree_refs_fk"
FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id)
    ON DELETE CASCADE NOT VALID;
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
ALTER TABLE "macrostrat"."strat_names_meta" ADD
CONSTRAINT "strat_names_meta_refs_fk"
FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) NOT VALID;
ALTER TABLE "macrostrat"."strat_names_meta" VALIDATE
CONSTRAINT "strat_names_meta_refs_fk";


-- 2026-01-05 11:23:52
-- Environment: local
-- 2 changes applied (1 unsafe)

ALTER TABLE "macrostrat"."strat_tree" DROP
CONSTRAINT "strat_tree_refs_fk";
ALTER TABLE "macrostrat"."strat_tree" ADD
CONSTRAINT "strat_tree_refs_fk"
FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) NOT VALID;

