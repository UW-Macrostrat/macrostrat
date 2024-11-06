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
DELETE FROM macrostrat.col_refs
	WHERE col_id NOT IN (SELECT id from macrostrat.cols)
	OR ref_id NOT IN (SELECT id from macrostrat.refs);

ALTER TABLE macrostrat.col_refs
	ADD CONSTRAINT col_refs_col_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE,
	ADD CONSTRAINT col_refs_ref_fk FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;

/* I had to make the id the primary key of intervals first before adding the foreign key */
ALTER TABLE macrostrat.intervals ADD PRIMARY KEY (id);

/* no issues
    col_notes were not perserved, in mariaDB this is a separte table.
*/
ALTER TABLE macrostrat.cols
	ADD CONSTRAINT cols_col_groups_fk FOREIGN KEY (col_group_id) REFERENCES macrostrat.col_groups(id) ON DELETE CASCADE;

/* no issues */
ALTER TABLE macrostrat.col_areas
	ADD CONSTRAINT col_areas_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

/* seems like the 'concepts' table is missing */
ALTER TABLE macrostrat.concepts_places
	ADD CONSTRAINT concepts_places_places_fk FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE;

/* 9 unit_id's deleted from unit_econs */
DELETE FROM macrostrat.unit_econs
	WHERE unit_id NOT IN (SELECT id from macrostrat.units);

ALTER TABLE macrostrat.unit_econs
	ADD CONSTRAINT unit_econs_econs_fk FOREIGN KEY (econ_id) REFERENCES macrostrat.econs(id) ON DELETE CASCADE,
	ADD CONSTRAINT unit_econs_refs_fk  FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE,
	ADD CONSTRAINT unit_econs_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

/*
23769 rows updated to have null ref_ids instead of 0...
*/
-- pg_loader apparently adds NOT NULL constraints in some cases
ALTER TABLE macrostrat.unit_environs ALTER COLUMN ref_id DROP NOT NULL;
UPDATE macrostrat.unit_environs
SET ref_id = NULL
WHERE ref_id = 0;

DELETE FROM macrostrat.unit_environs
WHERE unit_id not in (SELECT id from macrostrat.units);

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

/*
 deleted 2 rows from bad unit ids and 2 rows from bad strat_name ids

strat_name ids:
	the ids are just wrong. The strat_names exist but as different records than what is recorded..
	Need to update the table strat_name_ids where
	three sisters: 75254 -> 6040
	jasper fm: 102656 -> 102650

unit_ids:
	It appears that units were removed.. there are no units with the corresponding strat_names
*/
UPDATE macrostrat.unit_strat_names
SET strat_name_id = 6040
WHERE strat_name_id = 75254;

UPDATE macrostrat.unit_strat_names
SET strat_name_id = 102650
WHERE strat_name_id = 102656;

DELETE FROM macrostrat.unit_strat_names
	WHERE unit_id NOT IN (SELECT id from macrostrat.units);

ALTER TABLE macrostrat.unit_strat_names
	ADD CONSTRAINT unit_strat_names_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE,
	ADD CONSTRAINT unit_strat_names_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

-- Remove the NOT NULL constraint on concept_id
ALTER TABLE macrostrat.strat_names ALTER COLUMN concept_id DROP NOT NULL;
UPDATE macrostrat.strat_names
	SET concept_id = NULL
	WHERE concept_id = 0;

/* BREAKS!!! there is a non-null constraint on ref_id.. but 0 means none so. */
-- Remove the NOT NULL constraint on ref_id
ALTER TABLE macrostrat.strat_names ALTER COLUMN ref_id DROP NOT NULL;
UPDATE macrostrat.strat_names
	SET ref_id = NULL
	WHERE ref_id = 0;

DELETE FROM macrostrat.strat_names sn
WHERE sn.concept_id NOT IN (SELECT concept_id FROM macrostrat.strat_names_meta);

ALTER TABLE macrostrat.strat_names
	ADD CONSTRAINT strat_names_strat_names_meta_fk FOREIGN KEY (concept_id) REFERENCES macrostrat.strat_names_meta(concept_id) ON DELETE CASCADE;

-- There are 6,000+ strat_name_meta entries with interval_id = 0

ALTER TABLE macrostrat.strat_names_meta ALTER COLUMN interval_id DROP NOT NULL;
UPDATE macrostrat.strat_names_meta
  SET interval_id = NULL
  WHERE interval_id = 0;

ALTER TABLE macrostrat.strat_names_meta
	ADD CONSTRAINT strat_names_meta_intervals_fk FOREIGN KEY(interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE,
	ADD CONSTRAINT strat_names_meta_refs_fk FOREIGN KEY(ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;

/* 33 rows deleted b/c of non-matching strat_name ids
there doesn't seem to be a way to recover the missing strat_names
*/
DELETE FROM macrostrat.strat_names_places
	WHERE strat_name_id NOT IN (SELECT id from macrostrat.strat_names);

ALTER TABLE macrostrat.strat_names_places
	ADD CONSTRAINT strat_names_places_places_fk FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE,
	ADD CONSTRAINT strat_names_places_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

/* 1 row deleted b/c of bad interval id */
DELETE FROM macrostrat.timescales_intervals
	WHERE interval_id NOT IN (SELECT id from macrostrat.intervals);

ALTER TABLE macrostrat.timescales_intervals
	ADD CONSTRAINT timescales_intervals_timescales_fk FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE,
	ADD CONSTRAINT timescales_intervals_intervals_fk FOREIGN KEY (interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE;

/* 2 rows deleted for a col_id of 0,
one was a `test_delete_me`
the other was Lane Shale, unit_id 42143 */
DELETE FROM macrostrat.units
	WHERE col_id NOT IN (SELECT id FROM macrostrat.cols)
	-- Ensure that a maximum of two units are deleted, just for sanity.
  AND ((SELECT count(*) FROM macrostrat.units WHERE col_id = 0) <= 2);

/* Some units are not present in an existing section... */

-- 17 units exist with section_id = 0
-- 941 units exist with a section_id that is not a valid section

SELECT count(*) FROM macrostrat.units
WHERE section_id NOT IN (select id from macrostrat.sections);

UPDATE macrostrat.units
set section_id = NULL
where section_id not in (select id from macrostrat.sections);

ALTER TABLE macrostrat.units
	ADD CONSTRAINT units_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE,
	ADD CONSTRAINT units_sections_fk FOREIGN KEY (section_id) REFERENCES macrostrat.sections(id) ON DELETE CASCADE,
	ADD CONSTRAINT units_intervals_fo_fk FOREIGN KEY (fo) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE,
	ADD CONSTRAINT units_intervals_lo_fk FOREIGN KEY (lo) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.sections
	ADD CONSTRAINT sections_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

DELETE FROM macrostrat.strat_tree
	WHERE child NOT IN (SELECT id FROM macrostrat.strat_names)
	OR ref_id NOT IN (SELECT id FROM macrostrat.refs);

UPDATE macrostrat.strat_tree
	SET ref_id = NULL
	WHERE ref_id = 0;

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

UPDATE macrostrat.col_groups cg
SET project_id = c.project_id
FROM macrostrat.cols c
WHERE c.col_group_id = cg.id;


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

