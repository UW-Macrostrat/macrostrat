/* SQL script that
  - alters the MariaDB tables by adding a new column for geom -> text data,
  - sets the datatype of the new column data to WKT format,
  - drops the old geometry column,
  - adds default values for data formats that pgloader accepts

  NOTE: this runs in MariaDB, not PostgreSQL
 */

ALTER TABLE macrostrat_temp.pbdb_matches ADD COLUMN coordinate_point_text TEXT;

UPDATE macrostrat_temp.pbdb_matches SET coordinate_point_text = ST_AsText(coordinate);

ALTER TABLE macrostrat_temp.pbdb_matches DROP COLUMN coordinate;

UPDATE macrostrat_temp.pbdb_matches SET release_date = '2000-01-01' WHERE release_date = '0000-00-00 00:00:00';

ALTER TABLE macrostrat_temp.places ADD COLUMN geom_text LONGTEXT;

UPDATE macrostrat_temp.places
SET geom_text = ST_AsText(geom);
ALTER TABLE macrostrat_temp.places DROP COLUMN geom;


--Added query below to match the PG macrostrat database. Will need to review the API to ensure it doesn't break.
--https://github.com/UW-Macrostrat/macrostrat/blob/7aefe2d0cc89a738b356ff444b7b3dd0fd85e607/cli/macrostrat/cli/commands/table_meta/strat_tree/0-dump.sql
ALTER TABLE macrostrat_temp.strat_tree RENAME COLUMN this_name TO parent;
ALTER TABLE macrostrat_temp.strat_tree RENAME COLUMN that_name TO child;



ALTER TABLE macrostrat_temp.refs ADD COLUMN rgeom_text LONGTEXT;
UPDATE macrostrat_temp.refs
SET rgeom_text = ST_AsText(rgeom);
ALTER TABLE macrostrat_temp.refs DROP COLUMN rgeom;

UPDATE unit_contacts
-- Enum data type can't be null so set to enum option 'below'.
SET contact = 'below'
WHERE contact = '';

UPDATE unit_contacts
-- enum data type can't be null so set to enum option 'above'.
SET old_contact = 'above'
WHERE old_contact = '';

ALTER TABLE macrostrat_temp.cols ADD COLUMN coordinate_text LONGTEXT;
UPDATE macrostrat_temp.cols
SET coordinate_text = ST_AsText(coordinate);

ALTER TABLE macrostrat_temp.cols DROP COLUMN coordinate;

UPDATE macrostrat_temp.cols
SET created = '2000-01-01'
WHERE created = '0000-00-00 00:00:00';

ALTER TABLE macrostrat_temp.col_areas ADD COLUMN col_area_text LONGTEXT;

UPDATE macrostrat_temp.col_areas
SET col_areas.col_area_text = ST_AsText(col_area);

ALTER TABLE macrostrat_temp.col_areas DROP COLUMN col_area;

ALTER TABLE macrostrat_temp.col_areas_6April2016 ADD COLUMN col_area_text LONGTEXT;

UPDATE macrostrat_temp.col_areas_6April2016
SET col_areas_6April2016.col_area_text = ST_AsText(col_area);

ALTER TABLE macrostrat_temp.col_areas_6April2016 DROP COLUMN col_area;

UPDATE macrostrat_temp.liths
SET lith_group = NULL WHERE lith_group = '';
