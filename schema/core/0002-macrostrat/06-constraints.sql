
ALTER TABLE macrostrat.col_areas
  ADD CONSTRAINT col_areas_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.concepts_places
  ADD CONSTRAINT concepts_places_places_fk FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE,
  ADD CONSTRAINT concepts_places_concepts_fk FOREIGN KEY (concept_id) REFERENCES macrostrat.strat_names_meta(concept_id) ON DELETE CASCADE;

ALTER TABLE macrostrat.projects
  ADD CONSTRAINT projects_timescale_fk FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.projects_tree
  ADD CONSTRAINT projects_tree_child_id_fkey FOREIGN KEY (child_id) REFERENCES macrostrat.projects(id) ON UPDATE CASCADE ON DELETE CASCADE,
  ADD CONSTRAINT projects_tree_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES macrostrat.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE macrostrat.sections
  ADD CONSTRAINT sections_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.strat_names_places
  ADD CONSTRAINT strat_names_places_places_fk FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE,
  ADD CONSTRAINT strat_names_places_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.timescales_intervals
  ADD CONSTRAINT timescales_intervals_timescales_fk FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE,
  ADD CONSTRAINT timescales_intervals_intervals_fk FOREIGN KEY (interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.unit_liths
  ADD CONSTRAINT unit_liths_liths_fk FOREIGN KEY (lith_id) REFERENCES macrostrat.liths(id) ON DELETE CASCADE,
  ADD CONSTRAINT unit_liths_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.unit_environs
  ADD CONSTRAINT unit_environs_environs_fk FOREIGN KEY (environ_id) REFERENCES macrostrat.environs(id) ON DELETE CASCADE,
  ADD CONSTRAINT unit_environs_refs_fk  FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE,
  ADD CONSTRAINT unit_environs_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.unit_econs
  ADD CONSTRAINT unit_econs_econs_fk FOREIGN KEY (econ_id) REFERENCES macrostrat.econs(id) ON DELETE CASCADE,
  ADD CONSTRAINT unit_econs_refs_fk  FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE,
  ADD CONSTRAINT unit_econs_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.unit_liths_atts
  ADD CONSTRAINT unit_liths_atts_unit_liths_fk FOREIGN KEY (unit_lith_id) REFERENCES macrostrat.unit_liths(id) ON DELETE CASCADE,
  ADD CONSTRAINT unit_liths_atts_lith_atts_fk FOREIGN KEY (lith_att_id) REFERENCES macrostrat.lith_atts(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.unit_strat_names
  ADD CONSTRAINT unit_strat_names_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE,
  ADD CONSTRAINT unit_strat_names_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.unit_boundaries
  ADD FOREIGN KEY(unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE NOT VALID,
  ADD FOREIGN KEY(ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;

/**
  Unit-section relationships

  258 units are in more than one section/column
  TODO: we should decide if this will be allowed (i.e., do we put a unique constraint in units_sections?)

SELECT unit_id, array_agg(col_id), array_agg(section_id) FROM macrostrat.units_sections
GROUP BY unit_id
HAVING COUNT(unit_id) > 1;
*/

/**
  Really, units_sections should be a one-to-many data model, but it is implemented with the possibility of many-to-many relationships.
  Here, we add unique constraints and triggers to prevent many-to-many relationships.
**/

ALTER TABLE macrostrat.units_sections
  ADD CONSTRAINT units_sections_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE,
  ADD CONSTRAINT units_sections_sections_fk FOREIGN KEY (section_id) REFERENCES macrostrat.sections(id) ON DELETE CASCADE,
  ADD CONSTRAINT units_sections_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

-- ALTER TABLE macrostrat.units_sections
--   ADD CONSTRAINT unique_unit_section_col UNIQUE (unit_id, section_id, col_id) NOT VALID;

