import MySQLdb
import MySQLdb.cursors
import os
import psycopg2
from psycopg2.extensions import AsIs
import sys
import subprocess

sys.path = [os.path.join(os.path.dirname(__file__), os.pardir)] + sys.path
import credentials

# Connect to Postgres
pg_conn = psycopg2.connect(dbname=credentials.pg_db, user=credentials.pg_user, host=credentials.pg_host, port=credentials.pg_port)
pg_cur = pg_conn.cursor()

# Connect to MySQL
my_conn = MySQLdb.connect(host=credentials.mysql_host, user=credentials.mysql_user, passwd=credentials.mysql_passwd, db=credentials.mysql_db, unix_socket=credentials.mysql_socket, cursorclass=MySQLdb.cursors.DictCursor)
my_cur = my_conn.cursor()




# Start the process

# Remove existing CSVs
subprocess.call("rm *.csv", shell=True)

directory = os.getcwd()

params = {
  "unit_strat_names_path": directory + "/unit_strat_names.csv",
  "strat_names_path": directory + "/strat_names.csv",
  "units_sections_path": directory + "/units_sections.csv",
  "intervals_path": directory + "/intervals.csv",
  "lookup_unit_intervals_path": directory + "/lookup_unit_intervals.csv",
  "units_path": directory + "/units.csv",
  "lookup_strat_names_path": directory + "/lookup_strat_names.csv",
  "cols_path": directory + "/cols.csv",
  "col_areas_path": directory + "/col_areas.csv",
  "liths_path": directory + "/liths.csv",
  "lith_atts_path": directory + "/lith_atts.csv",
  "timescales_intervals_path": directory + "/timescales_intervals.csv",
  "unit_liths_path": directory + "/unit_liths.csv",
  "lookup_unit_liths_path": directory + "/lookup_unit_liths.csv",
  "timescales_path": directory + "/timescales.csv",
  "col_groups_path": directory + "/col_groups.csv",
  "col_refs_path": directory + "/col_refs.csv"
}




print "(1 of 3)   Dumping from MySQL"
my_cur.execute("""

  SELECT id, unit_id, strat_name_id
  FROM unit_strat_names
  INTO OUTFILE %(unit_strat_names_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT id, strat_name, rank, ref_id, concept_id
  FROM strat_names
  INTO OUTFILE %(strat_names_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT id, unit_id, section_id, col_id
  FROM units_sections
  INTO OUTFILE %(units_sections_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT id, age_bottom, age_top, interval_name, interval_abbrev, interval_type, interval_color
  FROM intervals
  INTO OUTFILE %(intervals_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT unit_id, fo_age, b_age, fo_interval, fo_period, lo_age, t_age, lo_interval, lo_period, age, age_id, epoch, epoch_id, period, period_id, era, era_id, eon, eon_id
  FROM lookup_unit_intervals
  INTO OUTFILE %(lookup_unit_intervals_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT id, strat_name, color, outcrop, FO, FO_h, LO, LO_h, position_bottom, position_top, max_thick, min_thick, section_id, col_id
  FROM units
  INTO OUTFILE %(units_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT strat_name_id, strat_name, rank, rank_name, bed_id, bed_name, mbr_id, mbr_name, fm_id, fm_name, gp_id, gp_name, sgp_id, sgp_name, early_age, late_age, gsc_lexicon, b_period, t_period, c_interval, name_no_lith
  FROM lookup_strat_names
  INTO OUTFILE %(lookup_strat_names_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT id, col_group_id, project_id, status_code, col_position, col, col_name, lat, lng, col_area, null AS coordinate, ST_AsText(coordinate) AS wkt, created
  FROM cols
  INTO OUTFILE %(cols_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT id, col_id, null as col_area, ST_AsText(col_area) AS wkt
  FROM col_areas
  INTO OUTFILE %(col_areas_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT id, lith, lith_type, lith_class, lith_fill, comp_coef, initial_porosity, bulk_density, lith_color
  FROM liths
  INTO OUTFILE %(liths_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT id, lith_att, att_type, lith_att_fill
  FROM lith_atts
  INTO OUTFILE %(lith_atts_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT timescale_id, interval_id
  FROM timescales_intervals
  INTO OUTFILE %(timescales_intervals_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT id, lith_id, unit_id, prop, dom, comp_prop, mod_prop, toc, ref_id
  FROM unit_liths
  INTO OUTFILE %(unit_liths_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT unit_id, lith_class, lith_type, lith_short, lith_long, environ_class, environ_type, environ
  FROM lookup_unit_liths
  INTO OUTFILE %(lookup_unit_liths_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT id, timescale, ref_id
  FROM timescales
  INTO OUTFILE %(timescales_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT id, col_group, col_group_long
  FROM col_groups
  INTO OUTFILE %(col_groups_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

  SELECT id, col_id, ref_id
  FROM col_refs
  INTO OUTFILE %(col_refs_path)s
  FIELDS TERMINATED BY ','
  ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

""", params)





subprocess.call("chmod 777 *.csv", shell=True)




print "(2 of 3)   Importing into Postgres"
pg_cur.execute("""
DROP SCHEMA IF EXISTS macrostrat_new cascade;
CREATE SCHEMA macrostrat_new;

CREATE TABLE macrostrat_new.unit_strat_names (
  id serial PRIMARY KEY NOT NULL,
  unit_id integer NOT NULL,
  strat_name_id integer NOT NULL
);

COPY macrostrat_new.unit_strat_names FROM %(unit_strat_names_path)s DELIMITER ',' CSV;

CREATE INDEX ON macrostrat_new.unit_strat_names (unit_id);
CREATE INDEX ON macrostrat_new.unit_strat_names (strat_name_id);


CREATE TABLE macrostrat_new.strat_names (
  id serial PRIMARY KEY NOT NULL,
  strat_name character varying(100) NOT NULL,
  rank character varying(50),
  ref_id  integer NOT NULL,
  concept_id integer
);

COPY macrostrat_new.strat_names FROM %(strat_names_path)s DELIMITER ',' CSV;

CREATE INDEX ON macrostrat_new.strat_names (strat_name);
CREATE INDEX ON macrostrat_new.strat_names (rank);
CREATE INDEX ON macrostrat_new.strat_names (ref_id);
CREATE INDEX ON macrostrat_new.strat_names (concept_id);


CREATE TABLE macrostrat_new.units_sections (
  id serial PRIMARY KEY NOT NULL,
  unit_id integer NOT NULL,
  section_id integer NOT NULL,
  col_id integer NOT NULL
);

COPY macrostrat_new.units_sections FROM %(units_sections_path)s DELIMITER ',' CSV;

CREATE INDEX ON macrostrat_new.units_sections (unit_id);
CREATE INDEX ON macrostrat_new.units_sections (section_id);
CREATE INDEX ON macrostrat_new.units_sections (col_id);

CREATE TABLE macrostrat_new.intervals (
  id serial NOT NULL,
  age_bottom numeric,
  age_top numeric,
  interval_name character varying(200),
  interval_abbrev character varying(50),
  interval_type character varying(50),
  interval_color character varying(20)
);

COPY macrostrat_new.intervals FROM %(intervals_path)s NULL '\N' DELIMITER ',' CSV;

ALTER TABLE macrostrat_new.intervals ADD COLUMN rank integer DEFAULT NULL;

INSERT INTO macrostrat_new.intervals (id, interval_name, interval_color) VALUES (0, 'Unknown', '#737373');

UPDATE macrostrat_new.intervals SET rank = 6 WHERE interval_type = 'age';
UPDATE macrostrat_new.intervals SET rank = 5 WHERE interval_type = 'epoch';
UPDATE macrostrat_new.intervals SET rank = 4 WHERE interval_type = 'period';
UPDATE macrostrat_new.intervals SET rank = 3 WHERE interval_type = 'era';
UPDATE macrostrat_new.intervals SET rank = 2 WHERE interval_type = 'eon';
UPDATE macrostrat_new.intervals SET rank = 1 WHERE interval_type = 'supereon';
UPDATE macrostrat_new.intervals SET rank = 0 WHERE rank IS NULL;

CREATE INDEX ON macrostrat_new.intervals (id);
CREATE INDEX ON macrostrat_new.intervals (age_top);
CREATE INDEX ON macrostrat_new.intervals (age_bottom);
CREATE INDEX ON macrostrat_new.intervals (interval_type);
CREATE INDEX ON macrostrat_new.intervals (interval_name);


CREATE TABLE macrostrat_new.lookup_unit_intervals (
  unit_id integer,
  FO_age numeric,
  b_age numeric,
  FO_interval character varying(50),
  FO_period character varying(50),
  LO_age numeric,
  t_age numeric,
  LO_interval character varying(50),
  LO_period character varying(50),
  age character varying(50),
  age_id integer,
  epoch character varying(50),
  epoch_id integer,
  period character varying(50),
  period_id integer,
  era character varying(50),
  era_id integer,
  eon character varying(50),
  eon_id integer
);

COPY macrostrat_new.lookup_unit_intervals FROM %(lookup_unit_intervals_path)s NULL '\N' DELIMITER ',' CSV;

ALTER TABLE macrostrat_new.lookup_unit_intervals ADD COLUMN best_interval_id integer;

WITH bests AS (
  select unit_id,
    CASE
      WHEN age_id > 0 THEN
        age_id
      WHEN epoch_id > 0 THEN
        epoch_id
      WHEN period_id > 0 THEN
        period_id
      WHEN era_id > 0 THEN
        era_id
      WHEN eon_id > 0 THEN
        eon_id
      ELSE
        0
    END
   AS b_interval_id from macrostrat_new.lookup_unit_intervals
)
UPDATE macrostrat_new.lookup_unit_intervals lui
SET best_interval_id = b_interval_id
FROM bests
WHERE lui.unit_id = bests.unit_id;

CREATE INDEX ON macrostrat_new.lookup_unit_intervals (unit_id);
CREATE INDEX ON macrostrat_new.lookup_unit_intervals (best_interval_id);



CREATE TABLE macrostrat_new.units (
  id integer PRIMARY KEY,
  strat_name character varying(150),
  color character varying(20),
  outcrop character varying(20),
  FO integer,
  FO_h integer,
  LO integer,
  LO_h integer,
  position_bottom numeric,
  position_top numeric,
  max_thick numeric,
  min_thick numeric,
  section_id integer,
  col_id integer
);

COPY macrostrat_new.units FROM %(units_path)s DELIMITER ',' CSV;


CREATE INDEX ON macrostrat_new.units (section_id);
CREATE INDEX ON macrostrat_new.units (col_id);
CREATE INDEX ON macrostrat_new.units (strat_name);
CREATE INDEX ON macrostrat_new.units (color);


CREATE TABLE macrostrat_new.lookup_strat_names (
  strat_name_id integer,
  strat_name character varying(100),
  rank character varying(20),
  rank_name character varying(200),
  bed_id integer,
  bed_name character varying(100),
  mbr_id integer,
  mbr_name character varying(100),
  fm_id integer,
  fm_name character varying(100),
  gp_id integer,
  gp_name character varying(100),
  sgp_id integer,
  sgp_name character varying(100),
  early_age numeric,
  late_age numeric,
  gsc_lexicon character varying(20),
  b_period character varying(100),
  t_period character varying(100),
  c_interval character varying(100),
  name_no_lith character varying(100)
);

COPY macrostrat_new.lookup_strat_names FROM %(lookup_strat_names_path)s NULL '\N' DELIMITER ',' CSV;


CREATE INDEX ON macrostrat_new.lookup_strat_names (strat_name_id);
CREATE INDEX ON macrostrat_new.lookup_strat_names (bed_id);
CREATE INDEX ON macrostrat_new.lookup_strat_names (mbr_id);
CREATE INDEX ON macrostrat_new.lookup_strat_names (fm_id);
CREATE INDEX ON macrostrat_new.lookup_strat_names (gp_id);
CREATE INDEX ON macrostrat_new.lookup_strat_names (sgp_id);
CREATE INDEX ON macrostrat_new.lookup_strat_names (strat_name);



CREATE TABLE macrostrat_new.cols (
  id integer PRIMARY KEY,
  col_group_id smallint,
  project_id smallint,
  status_code character varying(25),
  col_position character varying(25),
  col numeric,
  col_name character varying(100),
  lat numeric,
  lng numeric,
  col_area numeric,
  coordinate geometry,
  wkt text,
  created text
);

COPY macrostrat_new.cols FROM %(cols_path)s NULL '\N' DELIMITER ',' CSV;

UPDATE macrostrat_new.cols SET coordinate = ST_GeomFromText(wkt);
UPDATE macrostrat_new.cols SET coordinate = ST_GeomFromText(wkt);

CREATE INDEX ON macrostrat_new.cols (project_id);
CREATE INDEX ON macrostrat_new.cols USING GIST (coordinate);
CREATE INDEX ON macrostrat_new.cols (col_group_id);
CREATE INDEX ON macrostrat_new.cols (status_code);


CREATE TABLE macrostrat_new.col_areas (
  id integer PRIMARY KEY,
  col_id integer,
  col_area geometry,
  wkt text
);

COPY macrostrat_new.col_areas FROM %(col_areas_path)s NULL '\N' DELIMITER ',' CSV;

UPDATE macrostrat_new.col_areas SET col_area = ST_GeomFromText(wkt);

CREATE INDEX ON macrostrat_new.col_areas (col_id);
CREATE INDEX ON macrostrat_new.col_areas USING GIST (col_area);


ALTER TABLE macrostrat_new.cols ADD COLUMN poly_geom geometry;
UPDATE macrostrat_new.cols AS c
SET poly_geom = a.col_area
FROM macrostrat_new.col_areas a
WHERE c.id = a.col_id;

UPDATE macrostrat_new.cols SET poly_geom = ST_SetSRID(poly_geom, 4326);

CREATE INDEX ON macrostrat_new.cols USING GIST (poly_geom);


CREATE TABLE macrostrat_new.liths (
  id integer PRIMARY KEY NOT NULL,
  lith character varying(75),
  lith_type character varying(50),
  lith_class character varying(50),
  lith_fill integer,
  comp_coef numeric,
  initial_porosity numeric,
  bulk_density numeric,
  lith_color character varying(12)
);
COPY macrostrat_new.liths FROM %(liths_path)s NULL '\N' DELIMITER ',' CSV;

CREATE INDEX ON macrostrat_new.liths (lith);
CREATE INDEX ON macrostrat_new.liths (lith_class);
CREATE INDEX ON macrostrat_new.liths (lith_type);


CREATE TABLE macrostrat_new.lith_atts (
  id integer PRIMARY KEY NOT NULL,
  lith_att character varying(75),
  att_type character varying(25),
  lith_att_fill integer
);
COPY macrostrat_new.lith_atts FROM %(lith_atts_path)s NULL '\N' DELIMITER ',' CSV;

CREATE INDEX ON macrostrat_new.lith_atts (att_type);
CREATE INDEX ON macrostrat_new.lith_atts (lith_att);


CREATE TABLE macrostrat_new.timescales_intervals (
  timescale_id integer,
  interval_id integer
);
COPY macrostrat_new.timescales_intervals FROM %(timescales_intervals_path)s NULL '\N' DELIMITER ',' CSV;

CREATE INDEX ON macrostrat_new.timescales_intervals (timescale_id);
CREATE INDEX ON macrostrat_new.timescales_intervals (interval_id);


CREATE TABLE macrostrat_new.unit_liths (
  id integer PRIMARY KEY,
  lith_id integer,
  unit_id integer,
  prop text,
  dom character varying(10),
  comp_prop numeric,
  mod_prop numeric,
  toc numeric,
  ref_id integer
);

COPY macrostrat_new.unit_liths FROM %(unit_liths_path)s NULL '\N' DELIMITER ',' CSV;

CREATE INDEX ON macrostrat_new.unit_liths (unit_id);
CREATE INDEX ON macrostrat_new.unit_liths (lith_id);
CREATE INDEX ON macrostrat_new.unit_liths (ref_id);



CREATE TABLE macrostrat_new.lookup_unit_liths (
  unit_id integer,
  lith_class character varying(100),
  lith_type character varying(100),
  lith_short text,
  lith_long text,
  environ_class character varying(100),
  environ_type character varying(100),
  environ character varying(255)
);

COPY macrostrat_new.lookup_unit_liths FROM %(lookup_unit_liths_path)s NULL '\N' DELIMITER ',' CSV;

CREATE INDEX ON macrostrat_new.lookup_unit_liths (unit_id);



CREATE TABLE macrostrat_new.timescales (
  id integer PRIMARY KEY,
  timescale character varying(100),
  ref_id integer
);

COPY macrostrat_new.timescales FROM %(timescales_path)s NULL '\N' DELIMITER ',' CSV;

CREATE INDEX ON macrostrat_new.timescales(timescale);
CREATE INDEX ON macrostrat_new.timescales (ref_id);



CREATE TABLE macrostrat_new.col_groups (
    id integer PRIMARY KEY,
    col_group character varying(100),
    col_group_long character varying(100)
);

COPY macrostrat_new.col_groups FROM %(col_groups_path)s NULL '\N' DELIMITER ',' CSV;


CREATE TABLE macrostrat_new.col_refs (
    id integer PRIMARY KEY,
    col_id integer,
    ref_id integer
);
COPY macrostrat_new.col_refs FROM %(col_refs_path)s NULL '\N' DELIMITER ',' CSV;

CREATE INDEX ON macrostrat_new.col_refs (col_id);
CREATE INDEX ON macrostrat_new.col_refs (ref_id);

GRANT usage ON SCHEMA macrostrat TO readonly;
GRANT SELECT ON all tables IN SCHEMA macrostrat TO readonly;
""", params)
pg_conn.commit()





print "(3 of 3)   Vacuuming macrostrat"
pg_conn.set_isolation_level(0)
pg_cur.execute("VACUUM ANALYZE macrostrat_new.strat_names;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.unit_strat_names;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.units_sections;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.intervals;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.lookup_unit_intervals;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.units;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.lookup_strat_names;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.cols;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.col_areas;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.liths;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.lith_atts;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.timescales;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.col_groups;")
pg_cur.execute("VACUUM ANALYZE macrostrat_new.col_refs");
pg_cur.execute("""
  DROP SCHEMA IF EXISTS macrostrat cascade;
  ALTER SCHEMA macrostrat_new RENAME TO macrostrat;
""")
pg_conn.commit()


subprocess.call("rm *.csv", shell=True)



print "Done!"
