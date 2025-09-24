-- Column names unit_id	ref_id	section_id	section_name	country	province	lng	lat	paleolng	paleolat	unit_sum	unit_thickness	unit_thickness_sign	unit_thickness_unit	unit_con_base	unit_relationa	unit_relationb	unit_relationc	unit_paleoenvironment	depth_scale	group	formation	formation_thick_sign	formation_thick	formation_thick_unit	member	epoch	period	early_interval	late_interval	max_ma	min_ma	paleoenvironment	lithology1	lithology2	early_biozone	late_biozone

CREATE SCHEMA IF NOT EXISTS macrostrat_gbdb;

CREATE TABLE IF NOT EXISTS macrostrat_gbdb.strata (
  unit_id INTEGER,
  ref_id INTEGER,
  section_id INTEGER,
  section_name TEXT,
  country TEXT,
  province TEXT,
  lng NUMERIC,
  lat NUMERIC,
  paleolng NUMERIC,
  paleolat NUMERIC,
  unit_sum NUMERIC,
  unit_thickness NUMERIC,
  unit_thickness_sign TEXT,
  unit_thickness_unit TEXT,
  unit_con_base TEXT,
  unit_relationa TEXT,
  unit_relationb TEXT,
  unit_relationc TEXT,
  unit_paleoenvironment TEXT,
  depth_scale TEXT,
  "group" TEXT,
  formation TEXT,
  formation_thick_sign TEXT,
  formation_thick NUMERIC,
  formation_thick_unit TEXT,
  member TEXT,
  epoch TEXT,
  period TEXT,
  early_interval TEXT,
  late_interval TEXT,
  max_ma NUMERIC,
  min_ma NUMERIC,
  paleoenvironment TEXT,
  lithology1 TEXT,
  lithology2 TEXT,
  early_biozone TEXT,
  late_biozone TEXT
);

-- Path: '/Users/Daven/Projects/Macrostrat/Datasets/GBDB workshop/geological_strata.csv'

/** Command to load data:
  > cat "/Users/Daven/Projects/Macrostrat/Datasets/GBDB workshop/geological_strata.csv" \
  | macrostrat db psql -c 'COPY macrostrat_gbdb.strata FROM STDIN WITH CSV HEADER'
 */
