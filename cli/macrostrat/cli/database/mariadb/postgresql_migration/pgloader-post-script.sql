/*
 The query
 - Alters the MariaDB pbdb_matches table by adding a new column for the text data,
 - sets the datatype of the new column data to WKT format,
  - drops old geometry columns
 - refreshes the database after pgloader

 */

CREATE EXTENSION IF NOT EXISTS postgis;

SET search_path TO macrostrat_temp, public;

ALTER TABLE macrostrat_temp.pbdb_matches ADD COLUMN coordinate geometry(Point, 4326);
UPDATE macrostrat_temp.pbdb_matches SET coordinate = ST_GeomFromText(coordinate_point_text, 4326);
ALTER TABLE macrostrat_temp.pbdb_matches DROP COLUMN coordinate_point_text;
SELECT * FROM macrostrat_temp.pbdb_matches LIMIT 5;

ALTER TABLE macrostrat_temp.places ADD COLUMN geom geometry;
UPDATE macrostrat_temp.places SET geom = ST_GeomFromText(geom_text, 4326);

ALTER TABLE macrostrat_temp.places DROP COLUMN geom_text;
SELECT * FROM macrostrat_temp.places LIMIT 5;

ALTER TABLE macrostrat_temp.refs ADD COLUMN rgeom geometry;
UPDATE macrostrat_temp.refs SET rgeom = ST_GeomFromText(rgeom_text, 4326);
ALTER TABLE macrostrat_temp.refs DROP COLUMN rgeom_text;
SELECT * FROM macrostrat_temp.refs LIMIT 5;

ALTER TABLE macrostrat_temp.cols ADD COLUMN coordinate geometry;
UPDATE macrostrat_temp.cols SET coordinate = ST_GeomFromText(coordinate_text, 4326);
ALTER TABLE macrostrat_temp.cols DROP COLUMN coordinate_text;
SELECT * FROM macrostrat_temp.cols LIMIT 5;

ALTER TABLE macrostrat_temp.col_areas ADD COLUMN col_area geometry;
UPDATE macrostrat_temp.col_areas SET col_area = ST_GeomFromText(col_area_text, 4326);
ALTER TABLE macrostrat_temp.col_areas DROP COLUMN col_area_text;
SELECT * FROM macrostrat_temp.col_areas LIMIT 5;

ALTER TABLE macrostrat_temp.col_areas_6April2016 ADD COLUMN col_area geometry;
UPDATE macrostrat_temp.col_areas_6April2016 SET col_area = ST_GeomFromText(col_area_text, 4326);
ALTER TABLE macrostrat_temp.col_areas_6April2016 DROP COLUMN col_area_text;
SELECT * FROM macrostrat_temp.col_areas_6April2016 LIMIT 5;

--added query below since column exists in macrostrat and not in macrostrat_temp.
ALTER TABLE macrostrat_temp.measuremeta ADD COLUMN geometry geometry(Point, 4326);
UPDATE macrostrat_temp.measuremeta SET geometry = ST_SetSRID(ST_makepoint(lng, lat), 4326);

--added query below since column exists in macrostrat and not in macrostrat_temp.

ALTER TABLE macrostrat_temp.col_areas ADD COLUMN wkt text;
UPDATE macrostrat_temp.col_areas SET wkt = ST_AsText(col_area);

--added query below since column exists in macrostrat and not in macrostrat_temp.

ALTER TABLE macrostrat_temp.cols ADD COLUMN wkt text;
ALTER TABLE macrostrat_temp.cols ADD COLUMN poly_geom geometry;
UPDATE macrostrat_temp.cols SET wkt = ST_AsText(coordinate);
UPDATE macrostrat_temp.cols c SET poly_geom = a.col_area
FROM macrostrat_temp.col_areas a WHERE c.id = a.col_id;
UPDATE macrostrat_temp.cols SET poly_geom = ST_SetSRID(poly_geom, 4326);


--add rank column since this column only exists in macrostrat and not macrostrat_temp

ALTER TABLE macrostrat_temp.intervals ADD COLUMN rank integer;

