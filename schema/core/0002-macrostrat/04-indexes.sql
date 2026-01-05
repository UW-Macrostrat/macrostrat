CREATE INDEX col_areas_new_col_area_idx ON macrostrat.col_areas USING gist (col_area);

CREATE INDEX col_areas_new_col_id_idx ON macrostrat.col_areas USING btree (col_id);

CREATE INDEX col_groups_new_id_idx1 ON macrostrat.col_groups USING btree (id);

CREATE INDEX col_refs_new_col_id_idx1 ON macrostrat.col_refs USING btree (col_id);

CREATE INDEX col_refs_new_ref_id_idx1 ON macrostrat.col_refs USING btree (ref_id);

CREATE INDEX cols_new_col_group_id_idx ON macrostrat.cols USING btree (col_group_id);

CREATE INDEX cols_new_coordinate_idx ON macrostrat.cols USING gist (coordinate);

CREATE INDEX cols_new_poly_geom_idx ON macrostrat.cols USING gist (poly_geom);

CREATE INDEX cols_new_project_id_idx ON macrostrat.cols USING btree (project_id);

CREATE INDEX cols_new_status_code_idx ON macrostrat.cols USING btree (status_code);

CREATE INDEX concepts_places_new_concept_id_idx ON macrostrat.concepts_places USING btree (concept_id);

CREATE INDEX concepts_places_new_place_id_idx ON macrostrat.concepts_places USING btree (place_id);

CREATE INDEX idx_44157002_concept_id ON macrostrat.canada_lexicon_dump USING btree (concept_id);

CREATE INDEX idx_44157002_lower_interval_id ON macrostrat.canada_lexicon_dump USING btree (lower_interval_id);

CREATE INDEX idx_44157002_strat_name_id ON macrostrat.canada_lexicon_dump USING btree (strat_name_id);

CREATE INDEX idx_44157002_upper_interval_id ON macrostrat.canada_lexicon_dump USING btree (upper_interval_id);

CREATE INDEX idx_44157007_color ON macrostrat.colors USING btree (color);

CREATE UNIQUE INDEX idx_44157007_unit_hex ON macrostrat.colors USING btree (unit_hex);

CREATE INDEX idx_44157014_col_group_id ON macrostrat.cols USING btree (col_group_id);

CREATE INDEX idx_44157014_col_type ON macrostrat.cols USING btree (col_type);

CREATE INDEX idx_44157014_project_id ON macrostrat.cols USING btree (project_id);

CREATE INDEX idx_44157014_status_code ON macrostrat.cols USING btree (status_code);

CREATE INDEX idx_44157021_col_id ON macrostrat.col_areas USING btree (col_id);

CREATE INDEX idx_44157034_col_1 ON macrostrat.col_equiv USING btree (col_1);

CREATE INDEX idx_44157034_col_2 ON macrostrat.col_equiv USING btree (col_2);

CREATE INDEX idx_44157039_project_id ON macrostrat.col_groups USING btree (project_id);

CREATE INDEX idx_44157044_col_id ON macrostrat.col_notes USING btree (col_id);

CREATE INDEX idx_44157051_col_id ON macrostrat.col_refs USING btree (col_id);

CREATE INDEX idx_44157051_ref_id ON macrostrat.col_refs USING btree (ref_id);

CREATE INDEX idx_44157055_concept_id ON macrostrat.concepts_places USING btree (concept_id);

CREATE UNIQUE INDEX idx_44157055_concept_id_2 ON macrostrat.concepts_places USING btree (concept_id, place_id);

CREATE INDEX idx_44157055_place_id ON macrostrat.concepts_places USING btree (place_id);

CREATE INDEX idx_44157064_environ ON macrostrat.environs USING btree (environ);

CREATE INDEX idx_44157064_environ_class ON macrostrat.environs USING btree (environ_class);

CREATE INDEX idx_44157064_environ_type ON macrostrat.environs USING btree (environ_type);

CREATE INDEX idx_44157069__intervals_age_bottom ON macrostrat.intervals USING btree (age_bottom);

CREATE INDEX idx_44157069__intervals_age_top ON macrostrat.intervals USING btree (age_top);

CREATE INDEX idx_44157069__intervals_interval_type ON macrostrat.intervals USING btree (interval_type);

CREATE INDEX idx_44157069_interval_name ON macrostrat.intervals USING btree (interval_name);

CREATE INDEX idx_44157091_lith ON macrostrat.liths USING btree (lith);

CREATE INDEX idx_44157091_lith_class ON macrostrat.liths USING btree (lith_class);

CREATE INDEX idx_44157091_lith_type ON macrostrat.liths USING btree (lith_type);

CREATE INDEX idx_44157097_att_type ON macrostrat.lith_atts USING btree (att_type);

CREATE INDEX idx_44157097_equiv ON macrostrat.lith_atts USING btree (equiv);

CREATE INDEX idx_44157097_lith_att ON macrostrat.lith_atts USING btree (lith_att);

CREATE INDEX idx_44157101_lith_id ON macrostrat.lookup_measurements USING btree (lith_id);

CREATE INDEX idx_44157101_measure_phase ON macrostrat.lookup_measurements USING btree (measure_phase);

CREATE INDEX idx_44157101_measurement_class ON macrostrat.lookup_measurements USING btree (measurement_class);

CREATE INDEX idx_44157101_measurement_id ON macrostrat.lookup_measurements USING btree (measurement_id);

CREATE INDEX idx_44157101_measurement_type ON macrostrat.lookup_measurements USING btree (measurement_type);

CREATE INDEX idx_44157101_measuremeta_id ON macrostrat.lookup_measurements USING btree (measuremeta_id);

CREATE INDEX idx_44157101_ref_id ON macrostrat.lookup_measurements USING btree (ref_id);

CREATE INDEX idx_44157111_bed_id ON macrostrat.lookup_strat_names USING btree (bed_id);

CREATE INDEX idx_44157111_concept_id ON macrostrat.lookup_strat_names USING btree (concept_id);

CREATE INDEX idx_44157111_fm_id ON macrostrat.lookup_strat_names USING btree (fm_id);

CREATE INDEX idx_44157111_gp_id ON macrostrat.lookup_strat_names USING btree (gp_id);

CREATE INDEX idx_44157111_mbr_id ON macrostrat.lookup_strat_names USING btree (mbr_id);

CREATE INDEX idx_44157111_parent ON macrostrat.lookup_strat_names USING btree (parent);

CREATE INDEX idx_44157111_rank ON macrostrat.lookup_strat_names USING btree (rank);

CREATE INDEX idx_44157111_ref_id ON macrostrat.lookup_strat_names USING btree (ref_id);

CREATE INDEX idx_44157111_sgp_id ON macrostrat.lookup_strat_names USING btree (sgp_id);

CREATE INDEX idx_44157111_strat_name ON macrostrat.lookup_strat_names USING btree (strat_name);

CREATE INDEX idx_44157111_subgp_id ON macrostrat.lookup_strat_names USING btree (subgp_id);

CREATE INDEX idx_44157111_tree ON macrostrat.lookup_strat_names USING btree (tree);

CREATE INDEX idx_44157129_b_int ON macrostrat.lookup_units USING btree (b_int);

CREATE INDEX idx_44157129_project_id ON macrostrat.lookup_units USING btree (project_id);

CREATE INDEX idx_44157129_t_int ON macrostrat.lookup_units USING btree (t_int);

CREATE INDEX idx_44157155_unit_id_idx ON macrostrat.lookup_unit_attrs_api USING btree (unit_id);

CREATE INDEX idx_44157171_measurement_class ON macrostrat.measurements USING btree (measurement_class);

CREATE INDEX idx_44157171_measurement_type ON macrostrat.measurements USING btree (measurement_type);

CREATE INDEX idx_44157176_lith_att_id ON macrostrat.measuremeta USING btree (lith_att_id);

CREATE INDEX idx_44157176_lith_id ON macrostrat.measuremeta USING btree (lith_id);

CREATE INDEX idx_44157176_ref_id ON macrostrat.measuremeta USING btree (ref_id);

CREATE INDEX idx_44157186_col_id ON macrostrat.measuremeta_cols USING btree (col_id);

CREATE INDEX idx_44157186_measuremeta_id ON macrostrat.measuremeta_cols USING btree (measuremeta_id);

CREATE INDEX idx_44157191_measure_phase ON macrostrat.measures USING btree (measure_phase);

CREATE INDEX idx_44157191_measurement_id ON macrostrat.measures USING btree (measurement_id);

CREATE INDEX idx_44157191_measuremeta_id ON macrostrat.measures USING btree (measuremeta_id);

CREATE INDEX idx_44157191_method ON macrostrat.measures USING btree (method);

CREATE INDEX idx_44157212_bottom_depth ON macrostrat.offshore_baggage USING btree (bottom_depth);

CREATE INDEX idx_44157212_cleaned_lith ON macrostrat.offshore_baggage USING btree (cleaned_lith);

CREATE INDEX idx_44157212_cleaned_minor ON macrostrat.offshore_baggage USING btree (cleaned_minor);

CREATE INDEX idx_44157212_col_id ON macrostrat.offshore_baggage USING btree (col_id);

CREATE INDEX idx_44157212_principal_lith_prefix_cleaned ON macrostrat.offshore_baggage USING btree (principal_lith_prefix_cleaned);

CREATE INDEX idx_44157212_principal_lithology_name ON macrostrat.offshore_baggage USING btree (principal_lithology_name);

CREATE INDEX idx_44157212_principal_lithology_prefix ON macrostrat.offshore_baggage USING btree (principal_lithology_prefix);

CREATE INDEX idx_44157212_principal_lithology_suffix ON macrostrat.offshore_baggage USING btree (principal_lithology_suffix);

CREATE INDEX idx_44157212_section_id ON macrostrat.offshore_baggage USING btree (section_id);

CREATE INDEX idx_44157212_top_depth ON macrostrat.offshore_baggage USING btree (top_depth);

CREATE INDEX idx_44157222_col_id ON macrostrat.offshore_fossils USING btree (col_id);

CREATE INDEX idx_44157222_section_id ON macrostrat.offshore_fossils USING btree (section_id);

CREATE INDEX idx_44157222_taxa ON macrostrat.offshore_fossils USING btree (taxa);

CREATE INDEX idx_44157222_unit_id ON macrostrat.offshore_fossils USING btree (unit_id);

CREATE INDEX idx_44157230_col_id ON macrostrat.offshore_hole_ages USING btree (col_id);

CREATE INDEX idx_44157230_interval_id ON macrostrat.offshore_hole_ages USING btree (interval_id);

CREATE INDEX idx_44157234_col_id ON macrostrat.offshore_sections USING btree (col_id);

CREATE INDEX idx_44157237_col_group_id ON macrostrat.offshore_sites USING btree (col_group_id);

CREATE INDEX idx_44157237_col_id ON macrostrat.offshore_sites USING btree (col_id);

CREATE INDEX idx_44157237_leg ON macrostrat.offshore_sites USING btree (leg);

CREATE INDEX idx_44157237_ref_id ON macrostrat.offshore_sites USING btree (ref_id);

CREATE INDEX idx_44157237_site ON macrostrat.offshore_sites USING btree (site);

CREATE INDEX idx_44157241__intervals_age_bottom ON macrostrat.pbdb_intervals USING btree (age_bottom);

CREATE INDEX idx_44157241__intervals_age_top ON macrostrat.pbdb_intervals USING btree (age_top);

CREATE INDEX idx_44157241__intervals_interval_type ON macrostrat.pbdb_intervals USING btree (interval_type);

CREATE INDEX idx_44157241_interval_name ON macrostrat.pbdb_intervals USING btree (interval_name);

CREATE INDEX idx_44157254_collection_no ON macrostrat.pbdb_matches USING btree (collection_no);

CREATE INDEX idx_44157254_ref_id ON macrostrat.pbdb_matches USING btree (ref_id);

CREATE INDEX idx_44157254_unit_id ON macrostrat.pbdb_matches USING btree (unit_id);

CREATE INDEX idx_44157270_project ON macrostrat.projects USING btree (project);

CREATE INDEX idx_44157270_timescale_id ON macrostrat.projects USING btree (timescale_id);

CREATE INDEX idx_44157286_feature_class ON macrostrat.rockd_features USING btree (feature_class);

CREATE INDEX idx_44157286_feature_type ON macrostrat.rockd_features USING btree (feature_type);

CREATE INDEX idx_44157290_interval_id ON macrostrat.ronov_sediment USING btree (interval_id);

CREATE INDEX idx_44157294_col_id ON macrostrat.sections USING btree (col_id);

CREATE INDEX idx_44157294_fo ON macrostrat.sections USING btree (fo);

CREATE INDEX idx_44157294_lo ON macrostrat.sections USING btree (lo);

CREATE INDEX idx_44157311_concept_id ON macrostrat.strat_names USING btree (concept_id);

CREATE INDEX idx_44157311_rank ON macrostrat.strat_names USING btree (rank);

CREATE INDEX idx_44157311_ref_id ON macrostrat.strat_names USING btree (ref_id);

CREATE INDEX idx_44157311_strat_name ON macrostrat.strat_names USING btree (strat_name);

CREATE INDEX idx_44157318_bed_id ON macrostrat.strat_names_lookup USING btree (bed_id);

CREATE INDEX idx_44157318_fm_id ON macrostrat.strat_names_lookup USING btree (fm_id);

CREATE INDEX idx_44157318_gp_id ON macrostrat.strat_names_lookup USING btree (gp_id);

CREATE INDEX idx_44157318_mbr_id ON macrostrat.strat_names_lookup USING btree (mbr_id);

CREATE INDEX idx_44157318_sgp_id ON macrostrat.strat_names_lookup USING btree (sgp_id);

CREATE INDEX idx_44157324_b_int ON macrostrat.strat_names_meta USING btree (b_int);

CREATE INDEX idx_44157324_interval_id ON macrostrat.strat_names_meta USING btree (interval_id);

CREATE INDEX idx_44157324_ref_id ON macrostrat.strat_names_meta USING btree (ref_id);

CREATE INDEX idx_44157324_t_int ON macrostrat.strat_names_meta USING btree (t_int);

CREATE UNIQUE INDEX idx_44157331_strat_name_id ON macrostrat.strat_names_places USING btree (strat_name_id, place_id);

CREATE INDEX idx_44157354_col_id ON macrostrat.temp_areas USING btree (col_id);

CREATE UNIQUE INDEX idx_44157354_col_id_2 ON macrostrat.temp_areas USING btree (col_id);

CREATE INDEX idx_44157358_ref_id ON macrostrat.timescales USING btree (ref_id);

CREATE INDEX idx_44157358_timescale ON macrostrat.timescales USING btree (timescale);

CREATE INDEX idx_44157363__timescale_intervals_interval_id ON macrostrat.timescales_intervals USING btree (interval_id);

CREATE INDEX idx_44157363__timescale_intervals_timescale_id ON macrostrat.timescales_intervals USING btree (timescale_id);

CREATE INDEX idx_44157375_col_id ON macrostrat.units USING btree (col_id);

CREATE INDEX idx_44157375_color ON macrostrat.units USING btree (color);

CREATE INDEX idx_44157375_fo ON macrostrat.units USING btree (fo);

CREATE INDEX idx_44157375_lo ON macrostrat.units USING btree (lo);

CREATE INDEX idx_44157375_section_id ON macrostrat.units USING btree (section_id);

CREATE INDEX idx_44157375_strat_name ON macrostrat.units USING btree (strat_name);

CREATE INDEX idx_44157384_datafile_id ON macrostrat.units_datafiles USING btree (datafile_id);

CREATE INDEX idx_44157388_col_id ON macrostrat.units_sections USING btree (col_id);

CREATE INDEX idx_44157388_section_id ON macrostrat.units_sections USING btree (section_id);

CREATE INDEX idx_44157388_unit_id ON macrostrat.units_sections USING btree (unit_id);

CREATE INDEX idx_44157393_section_id ON macrostrat.unit_boundaries USING btree (section_id);

CREATE INDEX idx_44157393_t1 ON macrostrat.unit_boundaries USING btree (t1);

CREATE INDEX idx_44157393_unit_id ON macrostrat.unit_boundaries USING btree (unit_id);

CREATE INDEX idx_44157393_unit_id_2 ON macrostrat.unit_boundaries USING btree (unit_id_2);

CREATE INDEX idx_44157404_section_id ON macrostrat.unit_boundaries_backup USING btree (section_id);

CREATE INDEX idx_44157404_t1 ON macrostrat.unit_boundaries_backup USING btree (t1);

CREATE INDEX idx_44157404_unit_id ON macrostrat.unit_boundaries_backup USING btree (unit_id);

CREATE INDEX idx_44157404_unit_id_2 ON macrostrat.unit_boundaries_backup USING btree (unit_id_2);

CREATE INDEX idx_44157415_section_id ON macrostrat.unit_boundaries_scratch USING btree (section_id);

CREATE INDEX idx_44157415_t1 ON macrostrat.unit_boundaries_scratch USING btree (t1);

CREATE INDEX idx_44157415_unit_id ON macrostrat.unit_boundaries_scratch USING btree (unit_id);

CREATE INDEX idx_44157415_unit_id_2 ON macrostrat.unit_boundaries_scratch USING btree (unit_id_2);

CREATE INDEX idx_44157426_section_id ON macrostrat.unit_boundaries_scratch_old USING btree (section_id);

CREATE INDEX idx_44157426_t1 ON macrostrat.unit_boundaries_scratch_old USING btree (t1);

CREATE INDEX idx_44157426_unit_id ON macrostrat.unit_boundaries_scratch_old USING btree (unit_id);

CREATE INDEX idx_44157426_unit_id_2 ON macrostrat.unit_boundaries_scratch_old USING btree (unit_id_2);

CREATE INDEX idx_44157435_unit_id ON macrostrat.unit_contacts USING btree (unit_id);

CREATE INDEX idx_44157435_with_unit ON macrostrat.unit_contacts USING btree (with_unit);

CREATE INDEX idx_44157440_ref_id ON macrostrat.unit_dates USING btree (ref_id);

CREATE INDEX idx_44157440_unit_id ON macrostrat.unit_dates USING btree (unit_id);

CREATE INDEX idx_44157447_econ_id ON macrostrat.unit_econs USING btree (econ_id);

CREATE INDEX idx_44157447_ref_id ON macrostrat.unit_econs USING btree (ref_id);

CREATE INDEX idx_44157447_unit_id ON macrostrat.unit_econs USING btree (unit_id);

CREATE INDEX idx_44157452_environ_id ON macrostrat.unit_environs USING btree (environ_id);

CREATE INDEX idx_44157452_ref_id ON macrostrat.unit_environs USING btree (ref_id);

CREATE INDEX idx_44157452_unit_id ON macrostrat.unit_environs USING btree (unit_id);

CREATE INDEX idx_44157458_new_unit_id ON macrostrat.unit_equiv USING btree (new_unit_id);

CREATE INDEX idx_44157458_unit_id ON macrostrat.unit_equiv USING btree (unit_id);

CREATE INDEX idx_44157463_lith_id ON macrostrat.unit_liths USING btree (lith_id);

CREATE INDEX idx_44157463_ref_id ON macrostrat.unit_liths USING btree (ref_id);

CREATE INDEX idx_44157463_unit_id ON macrostrat.unit_liths USING btree (unit_id);

CREATE INDEX idx_44157469_lith_att_id ON macrostrat.unit_liths_atts USING btree (lith_att_id);

CREATE INDEX idx_44157469_ref_id ON macrostrat.unit_liths_atts USING btree (ref_id);

CREATE INDEX idx_44157469_unit_lith_id ON macrostrat.unit_liths_atts USING btree (unit_lith_id);

CREATE INDEX idx_44157474_measuremeta_id ON macrostrat.unit_measures USING btree (measuremeta_id);

CREATE INDEX idx_44157474_strat_name_id ON macrostrat.unit_measures USING btree (strat_name_id);

CREATE INDEX idx_44157474_unit_id ON macrostrat.unit_measures USING btree (unit_id);

CREATE INDEX idx_44157479_collection_no ON macrostrat.unit_measures_pbdb USING btree (collection_no);

CREATE INDEX idx_44157485_unit_id ON macrostrat.unit_notes USING btree (unit_id);

CREATE INDEX idx_44157492_unit_id ON macrostrat.unit_seq_strat USING btree (unit_id);

CREATE INDEX idx_44157497_strat_name_id ON macrostrat.unit_strat_names USING btree (strat_name_id);

CREATE INDEX idx_44157497_unit_id ON macrostrat.unit_strat_names USING btree (unit_id);

CREATE INDEX idx_44157502_tectonic_id ON macrostrat.unit_tectonics USING btree (tectonic_id);

CREATE INDEX idx_44157502_unit_id ON macrostrat.unit_tectonics USING btree (unit_id);

CREATE INDEX idx_projects_slug ON macrostrat.projects USING btree (slug);

CREATE INDEX intervals_new_age_bottom_idx1 ON macrostrat.intervals USING btree (age_bottom);

CREATE INDEX intervals_new_age_top_idx1 ON macrostrat.intervals USING btree (age_top);

CREATE INDEX intervals_new_id_idx1 ON macrostrat.intervals USING btree (id);

CREATE INDEX intervals_new_interval_name_idx1 ON macrostrat.intervals USING btree (interval_name);

CREATE INDEX intervals_new_interval_type_idx1 ON macrostrat.intervals USING btree (interval_type);

CREATE INDEX lith_atts_new_att_type_idx1 ON macrostrat.lith_atts USING btree (att_type);

CREATE INDEX lith_atts_new_lith_att_idx1 ON macrostrat.lith_atts USING btree (lith_att);

CREATE INDEX liths_new_lith_class_idx1 ON macrostrat.liths USING btree (lith_class);

CREATE INDEX liths_new_lith_idx1 ON macrostrat.liths USING btree (lith);

CREATE INDEX liths_new_lith_type_idx1 ON macrostrat.liths USING btree (lith_type);

CREATE INDEX lookup_strat_names_new_bed_id_idx ON macrostrat.lookup_strat_names USING btree (bed_id);

CREATE INDEX lookup_strat_names_new_concept_id_idx ON macrostrat.lookup_strat_names USING btree (concept_id);

CREATE INDEX lookup_strat_names_new_fm_id_idx ON macrostrat.lookup_strat_names USING btree (fm_id);

CREATE INDEX lookup_strat_names_new_gp_id_idx ON macrostrat.lookup_strat_names USING btree (gp_id);

CREATE INDEX lookup_strat_names_new_mbr_id_idx ON macrostrat.lookup_strat_names USING btree (mbr_id);

CREATE INDEX lookup_strat_names_new_sgp_id_idx ON macrostrat.lookup_strat_names USING btree (sgp_id);

CREATE INDEX lookup_strat_names_new_strat_name_id_idx ON macrostrat.lookup_strat_names USING btree (strat_name_id);

CREATE INDEX lookup_strat_names_new_strat_name_idx ON macrostrat.lookup_strat_names USING btree (strat_name);

CREATE INDEX lookup_unit_attrs_api_new_unit_id_idx1 ON macrostrat.lookup_unit_attrs_api USING btree (unit_id);

CREATE INDEX lookup_unit_intervals_new_best_interval_id_idx ON macrostrat.lookup_unit_intervals USING btree (best_interval_id);

CREATE INDEX lookup_unit_intervals_new_unit_id_idx ON macrostrat.lookup_unit_intervals USING btree (unit_id);

CREATE INDEX lookup_unit_liths_new_unit_id_idx ON macrostrat.lookup_unit_liths USING btree (unit_id);

CREATE INDEX lookup_units_new_b_int_idx1 ON macrostrat.lookup_units USING btree (b_int);

CREATE INDEX lookup_units_new_project_id_idx1 ON macrostrat.lookup_units USING btree (project_id);

CREATE INDEX lookup_units_new_t_int_idx1 ON macrostrat.lookup_units USING btree (t_int);

CREATE INDEX measurements_new_id_idx ON macrostrat.measurements USING btree (id);

CREATE INDEX measurements_new_measurement_class_idx ON macrostrat.measurements USING btree (measurement_class);

CREATE INDEX measurements_new_measurement_type_idx ON macrostrat.measurements USING btree (measurement_type);

CREATE INDEX measuremeta_new_lith_att_id_idx1 ON macrostrat.measuremeta USING btree (lith_att_id);

CREATE INDEX measuremeta_new_lith_id_idx1 ON macrostrat.measuremeta USING btree (lith_id);

CREATE INDEX measuremeta_new_ref_id_idx1 ON macrostrat.measuremeta USING btree (ref_id);

CREATE INDEX measures_new_measurement_id_idx1 ON macrostrat.measures USING btree (measurement_id);

CREATE INDEX measures_new_measuremeta_id_idx1 ON macrostrat.measures USING btree (measuremeta_id);

CREATE INDEX pbdb_collections_collection_no_idx ON macrostrat.pbdb_collections USING btree (collection_no);

CREATE INDEX pbdb_collections_collection_no_idx1 ON macrostrat.pbdb_collections USING btree (collection_no);

CREATE INDEX pbdb_collections_early_age_idx ON macrostrat.pbdb_collections USING btree (early_age);

CREATE INDEX pbdb_collections_early_age_idx1 ON macrostrat.pbdb_collections USING btree (early_age);

CREATE INDEX pbdb_collections_geom_idx ON macrostrat.pbdb_collections USING gist (geom);

CREATE INDEX pbdb_collections_geom_idx1 ON macrostrat.pbdb_collections USING gist (geom);

CREATE INDEX pbdb_collections_late_age_idx ON macrostrat.pbdb_collections USING btree (late_age);

CREATE INDEX pbdb_collections_late_age_idx1 ON macrostrat.pbdb_collections USING btree (late_age);

CREATE INDEX pbdb_collections_new_collection_no_idx1 ON macrostrat.pbdb_collections USING btree (collection_no);

CREATE INDEX pbdb_collections_new_early_age_idx1 ON macrostrat.pbdb_collections USING btree (early_age);

CREATE INDEX pbdb_collections_new_geom_idx1 ON macrostrat.pbdb_collections USING gist (geom);

CREATE INDEX pbdb_collections_new_late_age_idx1 ON macrostrat.pbdb_collections USING btree (late_age);

CREATE INDEX places_new_geom_idx ON macrostrat.places USING gist (geom);

CREATE INDEX projects_new_timescale_id_idx ON macrostrat.projects USING btree (timescale_id);

CREATE INDEX refs_new_rgeom_idx1 ON macrostrat.refs USING gist (rgeom);

CREATE INDEX sections_new_col_id_idx1 ON macrostrat.sections USING btree (col_id);

CREATE INDEX sections_new_id_idx1 ON macrostrat.sections USING btree (id);

CREATE INDEX strat_name_footprints_geom_idx ON macrostrat.strat_name_footprints USING gist (geom);

CREATE INDEX strat_name_footprints_geom_idx1 ON macrostrat.strat_name_footprints USING gist (geom);

CREATE INDEX strat_name_footprints_new_geom_idx ON macrostrat.strat_name_footprints USING gist (geom);

CREATE INDEX strat_name_footprints_new_strat_name_id_idx ON macrostrat.strat_name_footprints USING btree (strat_name_id);

CREATE INDEX strat_name_footprints_strat_name_id_idx ON macrostrat.strat_name_footprints USING btree (strat_name_id);

CREATE INDEX strat_name_footprints_strat_name_id_idx1 ON macrostrat.strat_name_footprints USING btree (strat_name_id);

CREATE INDEX strat_names_meta_new_b_int_idx1 ON macrostrat.strat_names_meta USING btree (b_int);

CREATE INDEX strat_names_meta_new_interval_id_idx1 ON macrostrat.strat_names_meta USING btree (interval_id);

CREATE INDEX strat_names_meta_new_ref_id_idx1 ON macrostrat.strat_names_meta USING btree (ref_id);

CREATE INDEX strat_names_meta_new_t_int_idx1 ON macrostrat.strat_names_meta USING btree (t_int);

CREATE INDEX strat_names_new_concept_id_idx ON macrostrat.strat_names USING btree (concept_id);

CREATE INDEX strat_names_new_rank_idx ON macrostrat.strat_names USING btree (rank);

CREATE INDEX strat_names_new_ref_id_idx ON macrostrat.strat_names USING btree (ref_id);

CREATE INDEX strat_names_new_strat_name_idx ON macrostrat.strat_names USING btree (strat_name);

CREATE INDEX strat_names_places_new_place_id_idx1 ON macrostrat.strat_names_places USING btree (place_id);

CREATE INDEX strat_names_places_new_strat_name_id_idx1 ON macrostrat.strat_names_places USING btree (strat_name_id);

CREATE INDEX timescales_intervals_new_interval_id_idx1 ON macrostrat.timescales_intervals USING btree (interval_id);

CREATE INDEX timescales_intervals_new_timescale_id_idx1 ON macrostrat.timescales_intervals USING btree (timescale_id);

CREATE INDEX timescales_new_ref_id_idx1 ON macrostrat.timescales USING btree (ref_id);

CREATE INDEX timescales_new_timescale_idx1 ON macrostrat.timescales USING btree (timescale);

CREATE INDEX unit_boundaries_section_id_idx ON macrostrat.unit_boundaries USING btree (section_id);

CREATE INDEX unit_boundaries_t1_idx ON macrostrat.unit_boundaries USING btree (t1);

CREATE INDEX unit_boundaries_unit_id_2_idx ON macrostrat.unit_boundaries USING btree (unit_id_2);

CREATE INDEX unit_boundaries_unit_id_idx ON macrostrat.unit_boundaries USING btree (unit_id);

CREATE INDEX unit_econs_new_econ_id_idx1 ON macrostrat.unit_econs USING btree (econ_id);

CREATE INDEX unit_econs_new_ref_id_idx1 ON macrostrat.unit_econs USING btree (ref_id);

CREATE INDEX unit_econs_new_unit_id_idx1 ON macrostrat.unit_econs USING btree (unit_id);

CREATE INDEX unit_environs_new_environ_id_idx1 ON macrostrat.unit_environs USING btree (environ_id);

CREATE INDEX unit_environs_new_ref_id_idx1 ON macrostrat.unit_environs USING btree (ref_id);

CREATE INDEX unit_environs_new_unit_id_idx1 ON macrostrat.unit_environs USING btree (unit_id);

CREATE INDEX unit_lith_atts_new_lith_att_id_idx1 ON macrostrat.unit_lith_atts USING btree (lith_att_id);

CREATE INDEX unit_lith_atts_new_ref_id_idx1 ON macrostrat.unit_lith_atts USING btree (ref_id);

CREATE INDEX unit_lith_atts_new_unit_lith_id_idx1 ON macrostrat.unit_lith_atts USING btree (unit_lith_id);

CREATE INDEX unit_liths_new_lith_id_idx1 ON macrostrat.unit_liths USING btree (lith_id);

CREATE INDEX unit_liths_new_ref_id_idx1 ON macrostrat.unit_liths USING btree (ref_id);

CREATE INDEX unit_liths_new_unit_id_idx1 ON macrostrat.unit_liths USING btree (unit_id);

CREATE INDEX unit_measures_new_measuremeta_id_idx ON macrostrat.unit_measures USING btree (measuremeta_id);

CREATE INDEX unit_measures_new_strat_name_id_idx ON macrostrat.unit_measures USING btree (strat_name_id);

CREATE INDEX unit_measures_new_unit_id_idx ON macrostrat.unit_measures USING btree (unit_id);

CREATE INDEX unit_strat_names_new_strat_name_id_idx1 ON macrostrat.unit_strat_names USING btree (strat_name_id);

CREATE INDEX unit_strat_names_new_unit_id_idx1 ON macrostrat.unit_strat_names USING btree (unit_id);

CREATE INDEX units_new_col_id_idx ON macrostrat.units USING btree (col_id);

CREATE INDEX units_new_color_idx ON macrostrat.units USING btree (color);

CREATE INDEX units_new_section_id_idx ON macrostrat.units USING btree (section_id);

CREATE INDEX units_new_strat_name_idx ON macrostrat.units USING btree (strat_name);

CREATE INDEX units_sections_new_col_id_idx ON macrostrat.units_sections USING btree (col_id);

CREATE INDEX units_sections_new_section_id_idx ON macrostrat.units_sections USING btree (section_id);

CREATE INDEX units_sections_new_unit_id_idx ON macrostrat.units_sections USING btree (unit_id);
