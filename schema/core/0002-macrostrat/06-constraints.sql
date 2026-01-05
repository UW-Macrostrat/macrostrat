ALTER TABLE ONLY macrostrat.col_areas
  ADD CONSTRAINT col_areas_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.col_refs
  ADD CONSTRAINT col_refs_col_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.col_refs
  ADD CONSTRAINT col_refs_ref_fk FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.cols
  ADD CONSTRAINT cols_col_groups_fk FOREIGN KEY (col_group_id) REFERENCES macrostrat.col_groups(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.cols
  ADD CONSTRAINT cols_project_fk FOREIGN KEY (project_id) REFERENCES macrostrat.projects(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.concepts_places
  ADD CONSTRAINT concepts_places_places_fk FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.projects
  ADD CONSTRAINT projects_timescale_fk FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.projects_tree
  ADD CONSTRAINT projects_tree_child_id_fkey FOREIGN KEY (child_id) REFERENCES macrostrat.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.projects_tree
  ADD CONSTRAINT projects_tree_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES macrostrat.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.sections
  ADD CONSTRAINT sections_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.strat_names_places
  ADD CONSTRAINT strat_names_places_places_fk FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.strat_names_places
  ADD CONSTRAINT strat_names_places_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.timescales_intervals
  ADD CONSTRAINT timescales_intervals_intervals_fk FOREIGN KEY (interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.timescales_intervals
  ADD CONSTRAINT timescales_intervals_timescales_fk FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.unit_econs
  ADD CONSTRAINT unit_econs_econs_fk FOREIGN KEY (econ_id) REFERENCES macrostrat.econs(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.unit_econs
  ADD CONSTRAINT unit_econs_refs_fk FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.unit_econs
  ADD CONSTRAINT unit_econs_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.unit_environs
  ADD CONSTRAINT unit_environs_environs_fk FOREIGN KEY (environ_id) REFERENCES macrostrat.environs(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.unit_environs
  ADD CONSTRAINT unit_environs_refs_fk FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.unit_environs
  ADD CONSTRAINT unit_environs_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.unit_liths_atts
  ADD CONSTRAINT unit_liths_atts_lith_atts_fk FOREIGN KEY (lith_att_id) REFERENCES macrostrat.lith_atts(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.unit_liths_atts
  ADD CONSTRAINT unit_liths_atts_unit_liths_fk FOREIGN KEY (unit_lith_id) REFERENCES macrostrat.unit_liths(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.unit_liths
  ADD CONSTRAINT unit_liths_liths_fk FOREIGN KEY (lith_id) REFERENCES macrostrat.liths(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.unit_liths
  ADD CONSTRAINT unit_liths_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.unit_strat_names
  ADD CONSTRAINT unit_strat_names_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.unit_strat_names
  ADD CONSTRAINT unit_strat_names_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.units
  ADD CONSTRAINT units_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.units
  ADD CONSTRAINT units_intervals_fo_fk FOREIGN KEY (fo) REFERENCES macrostrat.intervals(id) ON DELETE RESTRICT;

ALTER TABLE ONLY macrostrat.units
  ADD CONSTRAINT units_intervals_lo_fk FOREIGN KEY (lo) REFERENCES macrostrat.intervals(id) ON DELETE RESTRICT;

ALTER TABLE ONLY macrostrat.units
  ADD CONSTRAINT units_sections_fk FOREIGN KEY (section_id) REFERENCES macrostrat.sections(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.units_sections
  ADD CONSTRAINT units_sections_sections_fk FOREIGN KEY (section_id) REFERENCES macrostrat.sections(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat.units_sections
  ADD CONSTRAINT units_sections_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;
