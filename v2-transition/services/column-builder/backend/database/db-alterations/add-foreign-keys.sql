/* 
    A first round pass at adding EXPLICIT foreign keys to a postgres instance of macrostrat

    I will only add the deletes if there are conflicts on alters. And I'll mark what the issues are.
    But there are relatively recreateable

    Questions that arise:
        Where is project meta data? I.E name of project... etc. Theres a project_id in cols that I'm guessing
        references some table, perhaps in the mariaDB instance 

		It might be nice to add a status_code at the project level and not just column level. for navigating
		the api.

        What is cols.col? It doesn't seem to be unqiue, even within project.

        'concepts' table is missing
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

/* 23769 rows deleted because of bad reference ids... that seems like a lot */
DELETE FROM macrostrat.unit_environs
	WHERE ref_id NOT IN (SELECT id from macrostrat.refs);

ALTER TABLE macrostrat.unit_environs
	ADD FOREIGN KEY (environ_id) REFERENCES macrostrat.environs(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

/* no issues */
ALTER TABLE macrostrat.unit_liths
	ADD FOREIGN KEY (lith_id) REFERENCES macrostrat.liths(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;

/* no issues */
ALTER TABLE macrostrat.unit_lith_atts
	ADD FOREIGN KEY (unit_lith_id) REFERENCES macrostrat.unit_liths(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (lith_att_id) REFERENCES macrostrat.lith_atts(id) ON DELETE CASCADE;

/* deleted 2 rows from bad unit ids and 2 rows from bad strat_name ids*/
DELETE FROM macrostrat.unit_strat_names
	WHERE unit_id NOT IN (SELECT id from macrostrat.units)
    OR strat_name_id NOT IN (SELECT id from macrostrat.strat_names);

ALTER TABLE macrostrat.unit_strat_names
	ADD FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

/* 33 rows deleted b/c of non-matching strat_name ids */
DELETE FROM macrostrat.strat_names_places
	WHERE strat_name_id NOT IN (SELECT id from macrostrat.strat_names);

ALTER TABLE macrostrat.strat_names_places
	ADD FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE,
	ADD FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;

/* 1 row deleted b/c of bad interval id */
DELETE FROM macrostrat.timescales_intervals
	WHERE interval_id NOT IN (SELECT id from macrostrat.intervals);

/* I had to make the id the primary key of intervals first before adding the foreign key */
ALTER TABLE macrostrat.intervals
	ADD PRIMARY KEY (id);

ALTER TABLE macrostrat.timescales_intervals
	ADD FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE,
	ADD FOREIGN KEY (interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE;

/* 2 rows deleted for a col_id of 0, one was a `test_delete_me` */
DELETE FROM macrostrat.units
	WHERE col_id NOT IN (SELECT id FROM macrostrat.cols);

ALTER TABLE macrostrat.units
	ADD FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id);