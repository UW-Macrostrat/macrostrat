/** Validate constraints for schema Macrostrat **/

ALTER TABLE macrostrat.strat_names VALIDATE CONSTRAINT strat_names_strat_names_meta_fk;

-- DETAIL:  Key (project_id)=(0) is not present in table "projects".
ALTER TABLE macrostrat.col_groups VALIDATE CONSTRAINT col_groups_project_fk;

-- DETAIL:  Key (unit_id)=(0) is not present in table "units".
ALTER TABLE "macrostrat"."unit_boundaries" VALIDATE CONSTRAINT "unit_boundaries_unit_id_fkey";
