/*
Drop all views so they can be recreated.
TODO: automate this process.
*/
DROP VIEW IF EXISTS macrostrat_api.projects;
DROP VIEW IF EXISTS macrostrat_api.cols;
DROP VIEW IF EXISTS macrostrat_api.col_groups;
DROP VIEW IF EXISTS macrostrat_api.environs;
DROP VIEW IF EXISTS macrostrat_api.liths;
DROP VIEW IF EXISTS macrostrat_api.intervals;
DROP VIEW IF EXISTS macrostrat_api.timescales;
DROP VIEW IF EXISTS macrostrat_api.strat_tree;
DROP VIEW IF EXISTS macrostrat_api.refs;
DROP VIEW IF EXISTS macrostrat_api.units;
DROP VIEW IF EXISTS macrostrat_api.col_refs;
DROP VIEW IF EXISTS macrostrat_api.unit_environs;
DROP VIEW IF EXISTS macrostrat_api.unit_liths;
DROP VIEW IF EXISTS macrostrat_api.sections;
DROP VIEW IF EXISTS macrostrat_api.strat_names;
DROP VIEW IF EXISTS macrostrat_api.unit_strat_names;
DROP VIEW IF EXISTS macrostrat_api.units_strat_names;
DROP VIEW IF EXISTS macrostrat_api.strat_names_ref;
DROP VIEW IF EXISTS macrostrat_api.col_group_with_cols;
DROP VIEW IF EXISTS macrostrat_api.environ_unit;
DROP VIEW IF EXISTS macrostrat_api.econ_unit;
DROP VIEW IF EXISTS macrostrat_api.lith_attr_unit;
DROP VIEW IF EXISTS macrostrat_api.lith_unit;
DROP VIEW IF EXISTS macrostrat_api.unit_strat_name_expanded;
DROP VIEW IF EXISTS macrostrat_api.col_sections;
DROP VIEW IF EXISTS macrostrat_api.col_ref_expanded;
DROP VIEW IF EXISTS macrostrat_api.strat_names_meta;
DROP VIEW IF EXISTS macrostrat_api.unit_boundaries;
