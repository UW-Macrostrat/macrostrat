ALTER TABLE ONLY macrostrat.col_areas ALTER COLUMN id SET DEFAULT nextval('macrostrat.col_areas_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.col_equiv ALTER COLUMN id SET DEFAULT nextval('macrostrat.col_equiv_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.col_groups ALTER COLUMN id SET DEFAULT nextval('macrostrat.col_groups_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.col_notes ALTER COLUMN id SET DEFAULT nextval('macrostrat.col_notes_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.col_refs ALTER COLUMN id SET DEFAULT nextval('macrostrat.col_refs_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.cols ALTER COLUMN id SET DEFAULT nextval('macrostrat.cols_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.econs ALTER COLUMN id SET DEFAULT nextval('macrostrat.econs_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.environs ALTER COLUMN id SET DEFAULT nextval('macrostrat.environs_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.intervals ALTER COLUMN id SET DEFAULT nextval('macrostrat.intervals_new_id_seq1'::regclass);

ALTER TABLE ONLY macrostrat.lith_atts ALTER COLUMN id SET DEFAULT nextval('macrostrat.lith_atts_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.liths ALTER COLUMN id SET DEFAULT nextval('macrostrat.liths_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.measurements ALTER COLUMN id SET DEFAULT nextval('macrostrat.measurements_new_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.measuremeta ALTER COLUMN id SET DEFAULT nextval('macrostrat.measuremeta_new_id_seq1'::regclass);

ALTER TABLE ONLY macrostrat.measuremeta_cols ALTER COLUMN id SET DEFAULT nextval('macrostrat.measuremeta_cols_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.measures ALTER COLUMN id SET DEFAULT nextval('macrostrat.measures_new_id_seq1'::regclass);

ALTER TABLE ONLY macrostrat.offshore_hole_ages ALTER COLUMN id SET DEFAULT nextval('macrostrat.offshore_hole_ages_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.pbdb_intervals ALTER COLUMN id SET DEFAULT nextval('macrostrat.pbdb_intervals_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.pbdb_matches ALTER COLUMN id SET DEFAULT nextval('macrostrat.pbdb_matches_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.places ALTER COLUMN place_id SET DEFAULT nextval('macrostrat.places_place_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.projects ALTER COLUMN id SET DEFAULT nextval('macrostrat.projects_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.refs ALTER COLUMN id SET DEFAULT nextval('macrostrat.refs_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.rockd_features ALTER COLUMN id SET DEFAULT nextval('macrostrat.rockd_features_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.sections ALTER COLUMN id SET DEFAULT nextval('macrostrat.sections_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.strat_names ALTER COLUMN id SET DEFAULT nextval('macrostrat.strat_names_new_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.strat_names_meta ALTER COLUMN concept_id SET DEFAULT nextval('macrostrat.strat_names_meta_concept_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.structure_atts ALTER COLUMN id SET DEFAULT nextval('macrostrat.structure_atts_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.structures ALTER COLUMN id SET DEFAULT nextval('macrostrat.structures_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.tectonics ALTER COLUMN id SET DEFAULT nextval('macrostrat.tectonics_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.timescales ALTER COLUMN id SET DEFAULT nextval('macrostrat.timescales_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.uniquedatafiles2 ALTER COLUMN id SET DEFAULT nextval('macrostrat.uniquedatafiles2_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_boundaries ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_boundaries_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_boundaries_backup ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_boundaries_backup_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_boundaries_scratch ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_boundaries_scratch_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_boundaries_scratch_old ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_boundaries_scratch_old_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_contacts ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_contacts_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_dates ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_dates_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_econs ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_econs_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_environs ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_environs_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_equiv ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_equiv_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_liths ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_liths_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_liths_atts ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_liths_atts_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_measures ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_measures_new_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_notes ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_notes_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_seq_strat ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_seq_strat_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_strat_names ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_strat_names_new_id_seq1'::regclass);

ALTER TABLE ONLY macrostrat.unit_tectonics ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_tectonics_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.units ALTER COLUMN id SET DEFAULT nextval('macrostrat.units_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.units_sections ALTER COLUMN id SET DEFAULT nextval('macrostrat.units_sections_new_id_seq'::regclass);
