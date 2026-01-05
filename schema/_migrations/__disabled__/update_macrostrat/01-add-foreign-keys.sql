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

/* I had to make the id the primary key of intervals first before adding the foreign key */
-- ALTER TABLE macrostrat.intervals ADD PRIMARY KEY (id);

/* no issues
    col_notes were not perserved, in mariaDB this is a separte table.
*/

/* no issues */
ALTER TABLE macrostrat.col_areas
	ADD CONSTRAINT col_areas_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

/* seems like the 'concepts' table is missing */
ALTER TABLE macrostrat.concepts_places
	ADD CONSTRAINT concepts_places_places_fk FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE;

/*
23769 rows updated to have null ref_ids instead of 0...
*/
-- pg_loader apparently adds NOT NULL constraints in some cases
ALTER TABLE macrostrat.unit_environs ALTER COLUMN ref_id DROP NOT NULL;

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

-- There are 6,000+ strat_name_meta entries with interval_id = 0
ALTER TABLE macrostrat.strat_names_meta ALTER COLUMN interval_id DROP NOT NULL;

ALTER TABLE macrostrat.strat_names_places
	ADD CONSTRAINT strat_names_places_places_fk FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE,
	ADD CONSTRAINT strat_names_places_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.timescales_intervals
	ADD CONSTRAINT timescales_intervals_timescales_fk FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE,
	ADD CONSTRAINT timescales_intervals_intervals_fk FOREIGN KEY (interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.units_sections
  ADD CONSTRAINT units_sections_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE,
  ADD CONSTRAINT units_sections_sections_fk FOREIGN KEY (section_id) REFERENCES macrostrat.sections(id) ON DELETE CASCADE;


ALTER TABLE macrostrat.sections
	ADD CONSTRAINT sections_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.projects
	ADD CONSTRAINT projects_timescale_fk FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE;


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

