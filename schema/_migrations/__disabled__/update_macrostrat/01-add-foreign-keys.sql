/*
    A first round pass at adding EXPLICIT foreign keys to a postgres instance of macrostrat

    I will only add the deletes if there are conflicts on alters. And I'll mark what the issues are.
    But there are relatively recreateable

    Questions that arise:
        Where is project meta data? I.E name of project... etc. Theres a project_id in cols that I'm guessing
        references some table, perhaps in the mariaDB instance

		It might be nice to add a status_code at the project level and not just column level. for navigating
		the api.

        'sections' table is missing - columns have been added to 'units'
        'col_notes' table is missing
        'col_equv'  table is missing

*/

/* deleted 68 rows where col_id didn't exist in cols
    the mariadb version of macrostrat has a "col_equv" that maps
    the bad id-ed columns to the actual ones
 */
ALTER TABLE macrostrat.col_refs
	ADD CONSTRAINT col_refs_col_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE ON UPDATE CASCADE,
	ADD CONSTRAINT col_refs_ref_fk FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT col_refs_unique UNIQUE (col_id, ref_id);

/* I had to make the id the primary key of intervals first before adding the foreign key */
-- ALTER TABLE macrostrat.intervals ADD PRIMARY KEY (id);

ALTER TABLE macrostrat.col_groups
  ADD CONSTRAINT col_groups_project_fk FOREIGN KEY (project_id) REFERENCES macrostrat.projects(id) ON DELETE CASCADE ON UPDATE CASCADE;

/* no issues
    col_notes were not perserved, in mariaDB this is a separte table.
*/
ALTER TABLE macrostrat.cols
	ADD CONSTRAINT cols_col_groups_fk FOREIGN KEY (col_group_id) REFERENCES macrostrat.col_groups(id) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT cols_project_fk FOREIGN KEY (project_id) REFERENCES macrostrat.projects(id) ON DELETE CASCADE ON UPDATE CASCADE;

/* no issues */
ALTER TABLE macrostrat.col_areas
	ADD CONSTRAINT col_areas_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

/* seems like the 'concepts' table is missing */
ALTER TABLE macrostrat.concepts_places
	ADD CONSTRAINT concepts_places_places_fk FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE;

ALTER TABLE macrostrat.unit_econs
	ADD CONSTRAINT unit_econs_econs_fk FOREIGN KEY (econ_id) REFERENCES macrostrat.econs(id) ON DELETE CASCADE,
	ADD CONSTRAINT unit_econs_refs_fk  FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE,
	ADD CONSTRAINT unit_econs_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

/*
23769 rows updated to have null ref_ids instead of 0...
*/
-- pg_loader apparently adds NOT NULL constraints in some cases
ALTER TABLE macrostrat.unit_environs ALTER COLUMN ref_id DROP NOT NULL;

ALTER TABLE macrostrat.unit_environs
	ADD CONSTRAINT unit_environs_environs_fk FOREIGN KEY (environ_id) REFERENCES macrostrat.environs(id) ON DELETE CASCADE,
	ADD CONSTRAINT unit_environs_refs_fk  FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE,
	ADD CONSTRAINT unit_environs_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

/* no issues */
ALTER TABLE macrostrat.unit_liths
	ADD CONSTRAINT unit_liths_liths_fk FOREIGN KEY (lith_id) REFERENCES macrostrat.liths(id) ON DELETE CASCADE,
	ADD CONSTRAINT unit_liths_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

/* no issues */
-- now, we have renamed the table unit_lith_atts -> unit_liths_atts
ALTER TABLE macrostrat.unit_liths_atts
	ADD CONSTRAINT unit_liths_atts_unit_liths_fk FOREIGN KEY (unit_lith_id) REFERENCES macrostrat.unit_liths(id) ON DELETE CASCADE,
	ADD CONSTRAINT unit_liths_atts_lith_atts_fk FOREIGN KEY (lith_att_id) REFERENCES macrostrat.lith_atts(id) ON DELETE CASCADE;

DELETE FROM macrostrat.unit_strat_names
	WHERE unit_id NOT IN (SELECT id from macrostrat.units);

ALTER TABLE macrostrat.unit_strat_names
	ADD CONSTRAINT unit_strat_names_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE,
	ADD CONSTRAINT unit_strat_names_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

-- Remove the NOT NULL constraint on concept_id
ALTER TABLE macrostrat.strat_names ALTER COLUMN concept_id DROP NOT NULL;

ALTER TABLE macrostrat.strat_names ALTER COLUMN ref_id DROP NOT NULL;

ALTER TABLE macrostrat.strat_names
	ADD CONSTRAINT strat_names_strat_names_meta_fk FOREIGN KEY (concept_id) REFERENCES macrostrat.strat_names_meta(concept_id) ON DELETE CASCADE;

-- There are 6,000+ strat_name_meta entries with interval_id = 0

ALTER TABLE macrostrat.strat_names_meta ALTER COLUMN interval_id DROP NOT NULL;

ALTER TABLE macrostrat.strat_names_meta
	ADD CONSTRAINT strat_names_meta_intervals_fk FOREIGN KEY(interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE,
	ADD CONSTRAINT strat_names_meta_refs_fk FOREIGN KEY(ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.strat_names_places
	ADD CONSTRAINT strat_names_places_places_fk FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE,
	ADD CONSTRAINT strat_names_places_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.timescales_intervals
	ADD CONSTRAINT timescales_intervals_timescales_fk FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE,
	ADD CONSTRAINT timescales_intervals_intervals_fk FOREIGN KEY (interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.units_sections
  ADD CONSTRAINT units_sections_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE,
  ADD CONSTRAINT units_sections_sections_fk FOREIGN KEY (section_id) REFERENCES macrostrat.sections(id) ON DELETE CASCADE;


/* Some units are not tied to the correct sections... */
/** New addition 2024-11-06
  We want to keep the NOT NULL constraint on section_id (at least for now)
  so we have to reconstruct sections in a few cases.

- 17 units exist with section_id = 0
- 941 units exist with a section_id that is not a valid section,
  however all but 5 of those (all from New Zealand)
  have a valid section_id in the units_sections table.

  SELECT * FROM macrostrat.units
  WHERE section_id NOT IN (select id from macrostrat.sections)
  AND section_id NOT IN (SELECT id FROM macrostrat.sections);
*/


ALTER TABLE macrostrat.units
	ADD CONSTRAINT units_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE,
	ADD CONSTRAINT units_sections_fk FOREIGN KEY (section_id) REFERENCES macrostrat.sections(id) ON DELETE CASCADE,
	ADD CONSTRAINT units_intervals_fo_fk FOREIGN KEY (fo) REFERENCES macrostrat.intervals(id) ON DELETE RESTRICT,
	ADD CONSTRAINT units_intervals_lo_fk FOREIGN KEY (lo) REFERENCES macrostrat.intervals(id) ON DELETE RESTRICT;

ALTER TABLE macrostrat.sections
	ADD CONSTRAINT sections_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.strat_tree
	ADD CONSTRAINT strat_tree_strat_names_parent_fk FOREIGN KEY (parent) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE,
	ADD CONSTRAINT strat_tree_strat_names_child_fk FOREIGN KEY (child) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE,
	ADD CONSTRAINT strat_tree_refs_fk FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.projects
	ADD CONSTRAINT projects_timescale_fk FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE;

/* Set foreign key on col table */
ALTER TABLE macrostrat.cols
	ADD CONSTRAINT cols_project_fk  FOREIGN KEY (project_id) REFERENCES macrostrat.projects(id) ON DELETE CASCADE;

/* Add project id constraint to col-groups */
ALTER TABLE macrostrat.col_groups
	ADD COLUMN project_id INT REFERENCES macrostrat.projects(id);

--
-- /* unit_boundaries table, needs a unit_id and ref_id fk
-- 	lots of 0's in the unit_id row... not sure why
--  */
--
-- DELETE FROM macrostrat.unit_boundaries WHERE unit_id = 0 OR unit_id NOT IN (
-- 	SELECT id FROM macrostrat.units
-- );
--
-- ALTER TABLE macrostrat.unit_boundaries
-- 	ADD FOREIGN KEY(unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE,
-- 	ADD FOREIGN KEY(ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;
--
/* Best practices for hierarchal data in postgres??*/

