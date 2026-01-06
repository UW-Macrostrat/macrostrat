GRANT SELECT,USAGE ON SEQUENCE macrostrat.col_areas_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.col_equiv_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.col_groups_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.col_notes_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.col_refs_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.cols_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.econs_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.environs_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.intervals_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.intervals_new_id_seq1 TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.lith_atts_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.liths_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measurements_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measurements_new_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measuremeta_cols_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measuremeta_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measuremeta_new_id_seq1 TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measures_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measures_new_id_seq1 TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.offshore_hole_ages_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.pbdb_intervals_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.pbdb_matches_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.places_place_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.refs_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.rockd_features_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.strat_names_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.strat_names_meta_concept_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.strat_names_new_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.structure_atts_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.structures_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.tectonics_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.timescales_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.uniquedatafiles2_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_boundaries_backup_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_boundaries_scratch_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_boundaries_scratch_old_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_contacts_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_dates_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_econs_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_environs_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_equiv_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_liths_atts_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_liths_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_measures_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_measures_new_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_notes_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_seq_strat_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_strat_names_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_strat_names_new_id_seq1 TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_tectonics_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.units_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.units_sections_id_seq TO macrostrat;

GRANT SELECT,USAGE ON SEQUENCE macrostrat.units_sections_new_id_seq TO macrostrat;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat_admin IN SCHEMA macrostrat GRANT SELECT,USAGE ON SEQUENCES  TO macrostrat;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat_admin IN SCHEMA macrostrat GRANT SELECT ON TABLES  TO macrostrat;
