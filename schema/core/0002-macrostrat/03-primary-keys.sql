
ALTER TABLE ONLY macrostrat.grainsize
  ADD CONSTRAINT grainsize_pkey PRIMARY KEY (grain_id);

ALTER TABLE ONLY macrostrat.canada_lexicon_dump
  ADD CONSTRAINT idx_44157002_primary PRIMARY KEY (strat_unit_id);

ALTER TABLE ONLY macrostrat.col_areas
  ADD CONSTRAINT idx_44157021_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.col_notes
  ADD CONSTRAINT idx_44157044_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.econs
  ADD CONSTRAINT idx_44157059_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.environs
  ADD CONSTRAINT idx_44157064_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.liths
  ADD CONSTRAINT idx_44157091_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.lith_atts
  ADD CONSTRAINT idx_44157097_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.lookup_measurements
  ADD CONSTRAINT idx_44157101_primary PRIMARY KEY (measure_id);

ALTER TABLE ONLY macrostrat.lookup_strat_names
  ADD CONSTRAINT idx_44157111_primary PRIMARY KEY (strat_name_id);

ALTER TABLE ONLY macrostrat.lookup_units
  ADD CONSTRAINT idx_44157129_primary PRIMARY KEY (unit_id);

ALTER TABLE ONLY macrostrat.lookup_unit_intervals
  ADD CONSTRAINT idx_44157160_primary PRIMARY KEY (unit_id);

ALTER TABLE ONLY macrostrat.lookup_unit_liths
  ADD CONSTRAINT idx_44157165_primary PRIMARY KEY (unit_id);

ALTER TABLE ONLY macrostrat.measurements
  ADD CONSTRAINT idx_44157171_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.measuremeta
  ADD CONSTRAINT idx_44157176_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.measuremeta_cols
  ADD CONSTRAINT idx_44157186_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.measures
  ADD CONSTRAINT idx_44157191_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.minerals
  ADD CONSTRAINT idx_44157200_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.offshore_baggage
  ADD CONSTRAINT idx_44157212_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.offshore_baggage_units
  ADD CONSTRAINT idx_44157219_primary PRIMARY KEY (offshore_baggage_id);

ALTER TABLE ONLY macrostrat.offshore_fossils
  ADD CONSTRAINT idx_44157222_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.offshore_hole_ages
  ADD CONSTRAINT idx_44157230_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.offshore_sites
  ADD CONSTRAINT idx_44157237_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.pbdb_intervals
  ADD CONSTRAINT idx_44157241_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.pbdb_liths
  ADD CONSTRAINT idx_44157250_primary PRIMARY KEY (lith_id);

ALTER TABLE ONLY macrostrat.pbdb_matches
  ADD CONSTRAINT idx_44157254_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.places
  ADD CONSTRAINT idx_44157263_primary PRIMARY KEY (place_id);

ALTER TABLE ONLY macrostrat.rockd_features
  ADD CONSTRAINT idx_44157286_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.strat_names_lookup
  ADD CONSTRAINT idx_44157318_primary PRIMARY KEY (strat_name_id);

ALTER TABLE ONLY macrostrat.structures
  ADD CONSTRAINT idx_44157340_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.structure_atts
  ADD CONSTRAINT idx_44157345_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.tectonics
  ADD CONSTRAINT idx_44157350_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.timescales
  ADD CONSTRAINT idx_44157358_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.timescales_intervals
  ADD CONSTRAINT idx_44157363_primary PRIMARY KEY (timescale_id, interval_id);

ALTER TABLE ONLY macrostrat.uniquedatafiles2
  ADD CONSTRAINT idx_44157367_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.units_datafiles
  ADD CONSTRAINT idx_44157384_primary PRIMARY KEY (unit_id);

ALTER TABLE ONLY macrostrat.units_sections
  ADD CONSTRAINT idx_44157388_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_boundaries
  ADD CONSTRAINT idx_44157393_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_boundaries_backup
  ADD CONSTRAINT idx_44157404_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_boundaries_scratch
  ADD CONSTRAINT idx_44157415_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_boundaries_scratch_old
  ADD CONSTRAINT idx_44157426_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_contacts
  ADD CONSTRAINT idx_44157435_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_dates
  ADD CONSTRAINT idx_44157440_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_econs
  ADD CONSTRAINT idx_44157447_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_environs
  ADD CONSTRAINT idx_44157452_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_equiv
  ADD CONSTRAINT idx_44157458_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_liths
  ADD CONSTRAINT idx_44157463_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_liths_atts
  ADD CONSTRAINT idx_44157469_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_measures
  ADD CONSTRAINT idx_44157474_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_notes
  ADD CONSTRAINT idx_44157485_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_seq_strat
  ADD CONSTRAINT idx_44157492_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_strat_names
  ADD CONSTRAINT idx_44157497_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_tectonics
  ADD CONSTRAINT idx_44157502_primary PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_lith_atts
  ADD CONSTRAINT unit_lith_atts_new_pkey1 PRIMARY KEY (id);
