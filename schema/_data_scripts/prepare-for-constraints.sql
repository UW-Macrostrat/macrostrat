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

SET search_path TO macrostrat,public;

SELECT id
FROM macrostrat.cols
WHERE id NOT IN (SELECT col_id FROM macrostrat.col_refs);

SELECT col_id, count(*) FROM macrostrat.col_refs
GROUP BY col_id;

SELECT * FROM macrostrat.cols;

SELECT * FROM macrostrat.unit_econs
WHERE unit_id NOT IN (SELECT id from macrostrat.units);


/** Fix missing column refs */
WITH cols_without_refs AS (
  SELECT id
  FROM macrostrat.cols
  WHERE id NOT IN (SELECT col_id FROM macrostrat.col_refs)
), missing_refs AS (
  SELECT c.id, ce.col_1 former_col, cr.ref_id FROM cols_without_refs c
  JOIN macrostrat.col_equiv ce
    ON c.id = ce.col_2
  JOIN macrostrat.col_refs cr
    ON ce.col_1 = cr.col_id
)
INSERT INTO macrostrat.col_refs (col_id, ref_id)
SELECT id, ref_id
FROM missing_refs
ON CONFLICT (col_id) DO NOTHING;

SELECT * FROM macrostrat.cols
WHERE id > 1670 AND id < 1690;

SELECT
  col_1,
  col1.id col_1_id,
  col1.col_name col_1_name,
  col_2,
  col2.id col_2_id,
  col2.col_name col_2_name
FROM macrostrat.col_equiv ce
LEFT JOIN macrostrat.cols col1
  ON ce.col_1 = col1.id
LEFT JOIN macrostrat.cols col2
  ON ce.col_2 = col2.id;

SELECT * FROM macrostrat.col_refs
WHERE col_id NOT IN (SELECT id from macrostrat.cols)
   OR ref_id NOT IN (SELECT id from macrostrat.refs);

DO $$
BEGIN

-- Abort and roll back

/* deleted 68 rows where col_id didn't exist in cols
    the mariadb version of macrostrat has a "col_equv" that maps
    the bad id-ed columns to the actual ones
 */
DELETE FROM macrostrat.col_refs
WHERE col_id NOT IN (SELECT id from macrostrat.cols)
   OR ref_id NOT IN (SELECT id from macrostrat.refs);

/* 9 unit_id's deleted from unit_econs */
DELETE FROM macrostrat.unit_econs
WHERE unit_id NOT IN (SELECT id from macrostrat.units);

/*
23769 rows updated to have null ref_ids instead of 0...
*/
-- pg_loader apparently adds NOT NULL constraints in some cases
UPDATE macrostrat.unit_environs
SET ref_id = NULL
WHERE ref_id = 0;

DELETE FROM macrostrat.unit_environs
WHERE unit_id not in (SELECT id from macrostrat.units);

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

DELETE FROM macrostrat.strat_names sn
WHERE sn.concept_id NOT IN (SELECT concept_id FROM macrostrat.strat_names_meta);

/* 33 rows deleted b/c of non-matching strat_name ids
there doesn't seem to be a way to recover the missing strat_names
*/
DELETE FROM macrostrat.strat_names_places
WHERE strat_name_id NOT IN (SELECT id from macrostrat.strat_names);

/* 1 row deleted b/c of bad interval id */
DELETE FROM macrostrat.timescales_intervals
WHERE interval_id NOT IN (SELECT id from macrostrat.intervals);

/* 2 rows deleted for a col_id of 0,
one was a `test_delete_me`
the other was Lane Shale, unit_id 42143 */
DELETE FROM macrostrat.units
WHERE col_id NOT IN (SELECT id FROM macrostrat.cols)
  -- Ensure that a maximum of two units are deleted, just for sanity.
  AND ((SELECT count(*) FROM macrostrat.units WHERE col_id = 0) <= 2);


-- Create fk constraints on units_sections table
-- Delete bad units_sections record
DELETE FROM macrostrat.units_sections WHERE unit_id NOT IN (SELECT id FROM macrostrat.units);

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

/** Add sections to contain a few stray units from New Zealand */
WITH units AS (
  SELECT id, col_id, fo, lo, fo_h, lo_h
  FROM macrostrat.units
  WHERE id NOT IN (SELECT unit_id FROM macrostrat.units_sections)
    AND section_id NOT IN (SELECT id FROM macrostrat.sections)
  LIMIT 5 -- there should be only 5 units that match this criteria
), new_sections  AS (
  INSERT INTO macrostrat.sections (col_id, fo, lo, fo_h, lo_h)
    SELECT
      col_id, fo, lo, fo_h, lo_h
    FROM units
    GROUP BY col_id, fo, lo, fo_h, lo_h
    RETURNING col_id, id section_id
), new_units_sections AS (
  INSERT INTO macrostrat.units_sections (unit_id, section_id, col_id)
    SELECT u.id, ns.section_id, ns.col_id
    FROM units u
           JOIN new_sections ns
                ON u.col_id = ns.col_id
    RETURNING unit_id, section_id, col_id
)
-- Update legacy unit.section_id relationships to mirror the macrostrat.units_sections links
UPDATE macrostrat.units u
SET section_id = us.section_id
FROM new_units_sections us
WHERE u.id = us.unit_id
  AND u.col_id = us.col_id;


/** Update legacy section_id field for cases where it references a non-existent section.
TODO: we may want to delete this legacy field if it isn't needed.
*/
UPDATE macrostrat.units u
SET section_id = us.section_id
FROM macrostrat.units_sections us
WHERE u.id = us.unit_id
  AND u.col_id = us.col_id
  AND u.section_id NOT IN (SELECT id FROM macrostrat.sections);

/** Only a few units that are totally unlinked to sections
  SELECT * FROM macrostrat.units
  WHERE id NOT IN (SELECT unit_id FROM macrostrat.units_sections)
  AND section_id NOT IN (SELECT id FROM macrostrat.sections);

  -- fo, lo, fo_h and lo_h seem to match in all cases
 */


/* Reconstruct section_id field from units_sections table.
  TODO: the col_id and section_id fields in the "units_columns" table
   are the 'master' version of the link, and the others are around for
   legacy purposes.
*/
UPDATE macrostrat.units u
SET section_id = us.section_id,
    col_id = us.col_id
FROM macrostrat.units_sections us
WHERE u.id = us.unit_id
  AND u.section_id NOT IN (SELECT id FROM macrostrat.sections);

UPDATE macrostrat.strat_tree
SET ref_id = NULL
WHERE ref_id = 0;

SELECT parent, sn1.strat_name, sn1.ref_id FROM macrostrat.strat_tree st
JOIN macrostrat.strat_names sn1
  ON st.parent = sn1.id
WHERE st.ref_id NOT IN (SELECT id FROM macrostrat.refs);


SELECT * FROM macrostrat.strat_tree;
--WHERE child NOT IN (SELECT id FROM macrostrat.strat_names);

/** Major delete of strat_tree rows */
DELETE FROM macrostrat.strat_tree
WHERE child NOT IN (SELECT id FROM macrostrat.strat_names)
   OR ref_id NOT IN (SELECT id FROM macrostrat.refs);

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

ROLLBACK;

END;
$$ LANGUAGE plpgsql;
