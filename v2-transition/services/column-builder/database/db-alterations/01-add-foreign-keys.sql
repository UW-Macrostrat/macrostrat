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
	ADD FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;

/* I had to make the id the primary key of intervals first before adding the foreign key */
ALTER TABLE macrostrat.intervals
	ADD PRIMARY KEY (id);

/* no issues 
    col_notes were not perserved, in mariaDB this is a separte table.
*/
ALTER TABLE macrostrat.cols
	ADD FOREIGN KEY (col_group_id) REFERENCES macrostrat.col_groups(id) ON DELETE CASCADE;

/* no issues */
ALTER TABLE macrostrat.col_areas
	ADD FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

/* seems like the 'concepts' table is missing */
ALTER TABLE macrostrat.concepts_places
	ADD FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE;

/* 9 unit_id's deleted from unit_econs */
DELETE FROM macrostrat.unit_econs
	WHERE unit_id NOT IN (SELECT id from macrostrat.units);

ALTER TABLE macrostrat.unit_econs
	ADD FOREIGN KEY (econ_id) REFERENCES macrostrat.econs(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

/* 
23769 rows updated to have null ref_ids instead of 0...
*/
UPDATE macrostrat.unit_environs
SET ref_id = NULL
WHERE ref_id = 0;

DELETE FROM macrostrat.unit_environs
WHERE unit_id not in (SELECT id from macrostrat.units);

ALTER TABLE macrostrat.unit_environs
	ADD FOREIGN KEY (environ_id) REFERENCES macrostrat.environs(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

/* some 42k rows deleted */
DELETE FROM macrostrat.unit_liths
WHERE unit_id not in (SELECT id from macrostrat.units);

ALTER TABLE macrostrat.unit_liths
	ADD FOREIGN KEY (lith_id) REFERENCES macrostrat.liths(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

/* This deletes alot, and also sometimes hangs forever on the server... */
-- DELETE FROM macrostrat.unit_lith_atts
-- WHERE unit_lith_id not in (SELECT id from macrostrat.unit_liths);

-- ALTER TABLE macrostrat.unit_lith_atts
-- 	ADD FOREIGN KEY (unit_lith_id) REFERENCES macrostrat.unit_liths(id) ON DELETE CASCADE,
-- 	ADD FOREIGN KEY (lith_att_id) REFERENCES macrostrat.lith_atts(id) ON DELETE CASCADE;

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
	ADD FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.units_sections
	ADD FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (section_id) REFERENCES macrostrat.sections(id) ON DELETE CASCADE;
	ADD FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

UPDATE macrostrat.strat_names
	SET concept_id = NULL
	WHERE concept_id = 0;

/* BREAKS!!! there is a non-null constraint on ref_id.. but 0 means none so. */
UPDATE macrostrat.strat_names
	SET ref_id = NULL
	WHERE ref_id = 0;

DELETE FROM macrostrat.strat_names sn
WHERE sn.concept_id NOT IN (SELECT concept_id FROM macrostrat.strat_names_meta);

ALTER TABLE macrostrat.strat_names
	ADD FOREIGN KEY (concept_id) REFERENCES macrostrat.strat_names_meta(concept_id) ON DELETE CASCADE;

ALTER TABLE macrostrat.strat_names_meta
	ADD FOREIGN KEY(interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE,
	ADD FOREIGN KEY(ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;

/* 33 rows deleted b/c of non-matching strat_name ids 
there doesn't seem to be a way to recover the missing strat_names
*/
DELETE FROM macrostrat.strat_names_places
	WHERE strat_name_id NOT IN (SELECT id from macrostrat.strat_names);

ALTER TABLE macrostrat.strat_names_places
	ADD FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE,
	ADD FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

/* 1 row deleted b/c of bad interval id */
DELETE FROM macrostrat.timescales_intervals
	WHERE interval_id NOT IN (SELECT id from macrostrat.intervals);

ALTER TABLE macrostrat.timescales_intervals
	ADD FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE;

/* 2 rows deleted for a col_id of 0, 
one was a `test_delete_me` 
the other was Lane Shale, unit_id 42143
*/
DELETE FROM macrostrat.units
	WHERE col_id NOT IN (SELECT id FROM macrostrat.cols);

UPDATE macrostrat.units
set section_id = NULL
where section_id not in (select id from macrostrat.sections);

ALTER TABLE macrostrat.units
	ADD FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (section_id) REFERENCES macrostrat.sections(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (fo) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (lo) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.sections
	ADD FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;

INSERT INTO macrostrat.refs(id, pub_year, author, ref)VALUES(
	0,
	2022,
	'Unknown',
	'Catch all for 0 ref_ids'
);

DELETE FROM macrostrat.strat_tree
	WHERE child NOT IN (SELECT id FROM macrostrat.strat_names)
	OR ref_id NOT IN (SELECT id FROM macrostrat.refs);

ALTER TABLE macrostrat.strat_tree
	ADD FOREIGN KEY (parent) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (child) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;

ALTER TABLE macrostrat.projects
	ADD FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE;

/* Set foreign key on col table */
ALTER TABLE macrostrat.cols
	ADD FOREIGN KEY (project_id) REFERENCES macrostrat.projects(id) ON DELETE CASCADE;

/* Add project id constraint to col-groups */
ALTER TABLE macrostrat.col_groups
	ADD COLUMN project_id INT REFERENCES macrostrat.projects(id);

UPDATE macrostrat.col_groups cg
SET project_id = c.project_id
FROM macrostrat.cols c 
WHERE c.col_group_id = cg.id;


/* unit_boundaries table, needs a unit_id and ref_id fk
	lots of 0's in the unit_id row... not sure why
 */

DELETE FROM macrostrat.unit_boundaries WHERE unit_id = 0 OR unit_id NOT IN (
	SELECT id FROM macrostrat.units
);

ALTER TABLE macrostrat.unit_boundaries 
	ADD FOREIGN KEY(unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE,
	ADD FOREIGN KEY(ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;

/* Best practices for hierarchal data in postgres??*/

