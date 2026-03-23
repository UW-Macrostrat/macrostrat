SET search_path TO macrostrat, public;
ALTER TABLE IF EXISTS macrostrat.strat_name_footprints RENAME TO strat_name_footprints_old;
ALTER TABLE macrostrat.strat_name_footprints_new RENAME to strat_name_footprints;