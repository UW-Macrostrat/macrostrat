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

UPDATE macrostrat_gbdb.strata SET member = null WHERE member = '';
UPDATE macrostrat_gbdb.strata SET formation = null WHERE formation = '';
UPDATE macrostrat_gbdb.strata SET epoch = null WHERE epoch = '';

DROP VIEW macrostrat_api.gbdb_strata;
CREATE VIEW macrostrat_api.gbdb_strata AS
SELECT *,
       ((early_interval IS NOT NULL AND late_interval IS NOT NULL)
         OR (early_biozone IS NOT NULL AND late_biozone IS NOT NULL)
         OR (epoch IS NOT NULL)
         OR (period IS NOT NULL)
         OR (min_ma IS NOT NULL AND max_ma IS NOT NULL)) AS has_age_constraint
       FROM macrostrat_gbdb.strata;


-- 121903 strata have an age constraint
SELECT count(*) FROM macrostrat_api.gbdb_strata WHERE has_age_constraint;

--153217 strata do not have an age constraint
SELECT count(*) FROM macrostrat_api.gbdb_strata WHERE NOT has_age_constraint and (formation IS NOT NULL);

--153179 strata do not have an age constraint but have a formation name
SELECT count(*) FROM macrostrat_api.gbdb_strata WHERE NOT has_age_constraint;



-- 5742 formations mentioned that do not have an age constraint defined
SELECT count(DISTINCT formation)
FROM macrostrat_api.gbdb_strata
WHERE NOT has_age_constraint
  AND (formation IS NOT NULL);


SELECT DISTINCT (formation) formation
FROM macrostrat_api.gbdb_strata
WHERE NOT has_age_constraint
  AND (formation IS NOT NULL);

