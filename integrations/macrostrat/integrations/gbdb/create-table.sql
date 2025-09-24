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

SELECT count(*) FROM macrostrat_api.gbdb_strata WHERE (min_ma IS NOT NULL AND max_ma IS NOT NULL);


-- 121903 strata have an age constraint
SELECT count(*) FROM macrostrat_api.gbdb_strata WHERE has_age_constraint;

--153217 strata do not have an age constraint
SELECT count(*) FROM macrostrat_api.gbdb_strata WHERE NOT has_age_constraint;

--153179 strata do not have an age constraint but have a formation name
SELECT count(*) FROM macrostrat_api.gbdb_strata WHERE NOT has_age_constraint and (formation IS NOT NULL);



-- 5742 formations mentioned that do not have an age constraint defined
SELECT count(DISTINCT formation)
FROM macrostrat_api.gbdb_strata
WHERE NOT has_age_constraint
  AND (formation IS NOT NULL);


SELECT DISTINCT (formation) formation
FROM macrostrat_api.gbdb_strata
WHERE NOT has_age_constraint
  AND (formation IS NOT NULL);

-- Create an interval age range index
CREATE INDEX IF NOT EXISTS intervals_age_range_idx ON macrostrat.intervals ((age_bottom - age_top));

CREATE OR REPLACE FUNCTION macrostrat_api.interval_for_age_range(min_age NUMERIC, max_age NUMERIC) RETURNS INTEGER AS $$
SELECT id FROM macrostrat_api.intervals WHERE age_top <= min_age AND age_bottom >= max_age
  ORDER BY age_bottom-age_top
  LIMIT 1;
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION macrostrat_api.color_for_age_range(min_age NUMERIC, max_age NUMERIC) RETURNS TEXT AS $$
SELECT interval_color FROM macrostrat.intervals
WHERE id = macrostrat_api.interval_for_age_range(min_age, max_age)
LIMIT 1;
$$ LANGUAGE sql IMMUTABLE;


SELECT * FROM macrostrat.intervals WHERE id = macrostrat_api.interval_for_age_range(100, 140);


DROP TABLE IF EXISTS macrostrat_gbdb.sections CASCADE;
CREATE TABLE macrostrat_gbdb.sections AS
WITH a AS (SELECT section_id,
                  lng,
                  lat,
                  BOOL_OR(has_age_constraint) has_age_constraint,
                  MIN(min_ma)                 min_ma,
                  MAX(max_ma)                 max_ma
           FROM macrostrat_api.gbdb_strata
           GROUP BY section_id, lng, lat
)
SELECT *,
       macrostrat_api.color_for_age_range(a.min_ma, a.max_ma) color
FROM a;

SELECT * FROM macrostrat_gbdb.sections;

SELECT count(*) FROM macrostrat_api.gbdb_section WHERE has_age_constraint;

DROP VIEW IF EXISTS macrostrat_api.gbdb_section_geojson;
CREATE OR REPLACE VIEW macrostrat_api.gbdb_section_geojson AS
SELECT
  jsonb_build_object(
    'type',
    'FeatureCollection',
    'features',
    JSON_AGG(JSONB_BUILD_OBJECT(
      'geometry', ST_AsGeoJSON(ST_MakePoint(lng, lat))::jsonb,
      'type', 'Feature',
      'id', section_id,
      'properties', JSONB_BUILD_OBJECT(
        'section_id', section_id,
        'has_age_constraint', has_age_constraint,
        'color', color
      )
    ))
  ) geojson
FROM macrostrat_gbdb.sections;
