/** Validate constraints for schema Macrostrat **/

ALTER TABLE macrostrat.strat_names VALIDATE CONSTRAINT strat_names_strat_names_meta_fk;
ALTER TABLE macrostrat.col_groups VALIDATE CONSTRAINT col_groups_project_fk;

