-- Some fixes to imported strata
UPDATE macrostrat_gbdb.strata SET member = null WHERE member = '';
UPDATE macrostrat_gbdb.strata SET formation = null WHERE formation = '';
UPDATE macrostrat_gbdb.strata SET epoch = null WHERE epoch = '';


TRUNCATE TABLE macrostrat_gbdb.sections;
WITH a AS (SELECT section_id,
                  lng,
                  lat,
                  count(ac.t_age) > 0 has_age_constraint,
                  MIN(ac.t_age)                 min_ma,
                  MAX(ac.b_age)                 max_ma
  FROM macrostrat_gbdb.strata s
  LEFT JOIN macrostrat_gbdb.best_external_age_control ac
                            ON lower(s.formation) = lower(ac.name_clean)
                              AND lower(s.formation) != 'unknown'
           GROUP BY section_id, lng, lat
)
INSERT INTO macrostrat_gbdb.sections
SELECT *,
       macrostrat_api.color_for_age_range(a.min_ma, a.max_ma) color
FROM a;

TRUNCATE TABLE macrostrat_gbdb.summary_columns;
WITH hexgrid AS (
  SELECT ST_HexagonGrid(1, ST_MakeEnvelope(-180, -90, 180, 90, 4326)) AS hex
)
INSERT INTO macrostrat_gbdb.summary_columns
SELECT
    row_number() OVER () id,
    ST_ForceRHR((hex).geom) geometry
FROM hexgrid
WHERE ST_Intersects((hex).geom, (
    SELECT ST_Union(ST_SetSRID(ST_MakePoint(lng, lat), 4326)) FROM macrostrat_gbdb.sections WHERE has_age_constraint
  )
);


TRUNCATE TABLE macrostrat_gbdb.summary_units;
WITH col_sections AS (
  SELECT section_id, sc.id col_id
  FROM macrostrat_gbdb.sections s
         JOIN macrostrat_gbdb.summary_columns sc
              ON ST_Intersects(ST_SetSRID(ST_MakePoint(lng, lat), 4326), sc.geometry)
  WHERE has_age_constraint)
INSERT INTO macrostrat_gbdb.summary_units
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
