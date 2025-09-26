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

CREATE VIEW macrostrat_api.gbdb_formations AS
SELECT
  section_id,
  formation,
  MIN(min_ma) min_ma,
  MAX(max_ma) max_ma,
  MIN(unit_sum-unit_thickness) b_pos,
  MAX(unit_sum) t_pos,
  COUNT(*)
FROM macrostrat_gbdb.strata
GROUP BY section_id, formation;
-- TODO: get Macrostrat formations

SELECT
  section_id,
  formation,
  MIN(min_ma) min_ma,
  MAX(max_ma) max_ma,
  MIN(unit_sum-unit_thickness) b_pos,
  MAX(unit_sum) t_pos,
  COUNT(*),
  array_agg(DISTINCT lithology1)
FROM macrostrat_gbdb.strata
GROUP BY section_id, formation;


DROP VIEW macrostrat_api.gbdb_age_model;
CREATE OR REPLACE VIEW macrostrat_api.gbdb_age_model AS
WITH a0 AS (
  SELECT f.section_id,
    s.unit_id,
    f.formation,
    f.min_ma                  formation_min_ma,
    f.max_ma                  formation_max_ma,
    f.b_pos formation_b_pos,
    f.t_pos formation_t_pos,
    f.t_pos - f.b_pos formation_thickness,
    f.max_ma - f.min_ma formation_age_range,
    unit_sum - unit_thickness b_pos,
    unit_sum                  t_pos
  FROM macrostrat_gbdb.strata s
  JOIN macrostrat_api.gbdb_formations f
    ON s.section_id = f.section_id
   AND s.formation = f.formation
), with_proportions AS (SELECT *,
                               -- proportions through unit
                               (b_pos - formation_b_pos) / formation_thickness AS b_prop,
                               (t_pos - formation_b_pos) / formation_thickness AS t_prop
                        FROM a0
                        WHERE formation_thickness > 0
)
SELECT *,
       -- age estimates based on linear interpolation within formation
       formation_max_ma - b_prop * formation_age_range AS model_max_ma,
       formation_max_ma - t_prop * formation_age_range AS model_min_ma
FROM with_proportions;


/** Summary tables */

CREATE OR REPLACE VIEW macrostrat_api.gbdb_strata_with_age_model AS
SELECT s.*,
       am.model_min_ma,
       am.model_max_ma
FROM macrostrat_api.gbdb_strata s
       JOIN macrostrat_api.gbdb_age_model am
            ON s.section_id = am.section_id
              AND s.unit_id = am.unit_id;

DROP TABLE macrostrat_gbdb.summary_columns CASCADE;
CREATE TABLE macrostrat_gbdb.summary_columns AS
WITH hexgrid AS (
  SELECT ST_HexagonGrid(1, ST_MakeEnvelope(-180, -90, 180, 90, 4326)) AS hex
)
SELECT
  row_number() OVER () id,
  ST_ForceRHR((hex).geom) geometry
FROM hexgrid
WHERE ST_Intersects((hex).geom, (
    SELECT ST_Union(ST_SetSRID(ST_MakePoint(lng, lat), 4326)) FROM macrostrat_api.gbdb_section WHERE has_age_constraint
  )
);

DROP VIEW IF EXISTS macrostrat_api.gbdb_summary_columns;
CREATE OR REPLACE VIEW macrostrat_api.gbdb_summary_columns AS
SELECT jsonb_build_object(
    'type',
    'FeatureCollection',
    'features',
    JSON_AGG(JSONB_BUILD_OBJECT(
      'geometry', ST_AsGeoJSON(geometry)::jsonb,
      'type', 'Feature',
      'id', id,
      'properties', JSONB_BUILD_OBJECT(
        'section_id', id,
        'col_id', id
      )
    ))
  ) geojson
FROM macrostrat_gbdb.summary_columns;

DROP TABLE macrostrat_gbdb.summary_units CASCADE;
CREATE TABLE macrostrat_gbdb.summary_units AS
WITH col_sections AS (SELECT section_id, sc.id col_id
                      FROM macrostrat_gbdb.sections s
                             JOIN macrostrat_gbdb.summary_columns sc
                                  ON ST_Intersects(ST_SetSRID(ST_MakePoint(lng, lat), 4326), sc.geometry)
                      WHERE has_age_constraint)
SELECT
  row_number() OVER () unit_id,
  col_id,
  f.formation unit_name,
  min_ma t_age,
  max_ma b_age
FROM macrostrat_api.gbdb_formations f
JOIN col_sections cs ON cs.section_id = f.section_id
WHERE f.min_ma IS NOT NULL AND f.max_ma IS NOT NULL
GROUP BY col_id, f.formation, min_ma, max_ma;

DROP VIEW macrostrat_api.gbdb_summary_units;
CREATE VIEW macrostrat_api.gbdb_summary_units AS
SELECT * FROM macrostrat_gbdb.summary_units;

-- WITH duplicate_units AS (SELECT unit_id, section_id, COUNT(*)
--                FROM macrostrat_api.gbdb_strata
--                GROUP BY unit_id, section_id
--                HAVING COUNT(*) > 1
--                ORDER BY count DESC)
-- SELECT unit_id, array_agg(depth_scale) FROM duplicate_units
-- JOIN macrostrat_api.gbdb_strata USING (unit_id, section_id)
-- GROUP BY unit_id;
--
-- WITH duplicate_units AS (SELECT unit_id, section_id, COUNT(*)
--                          FROM macrostrat_api.gbdb_strata
--                          GROUP BY unit_id, section_id
--                          HAVING COUNT(*) > 1
--                          ORDER BY count DESC)
-- SELECT * FROM duplicate_units
-- JOIN macrostrat_api.gbdb_strata USING (unit_id, section_id);


WITH col_sections AS (SELECT section_id, sc.id col_id
                      FROM macrostrat_gbdb.sections s
                             JOIN macrostrat_gbdb.summary_columns sc
                                  ON ST_Intersects(ST_SetSRID(ST_MakePoint(lng, lat), 4326), sc.geometry)
                      WHERE has_age_constraint)
SELECT
    row_number() OVER () unit_id,
    col_id,
    f.formation unit_name,
    min_ma t_age,
    max_ma b_age
FROM macrostrat_api.gbdb_formations f
       JOIN col_sections cs ON cs.section_id = f.section_id
WHERE f.min_ma IS NOT NULL AND f.max_ma IS NOT NULL
GROUP BY col_id, f.formation, min_ma, max_ma;
