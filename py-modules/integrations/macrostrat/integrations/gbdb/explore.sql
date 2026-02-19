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


SELECT * FROM macrostrat.intervals WHERE id = macrostrat_api.interval_for_age_range(100, 140);


SELECT count(*) FROM macrostrat_gbdb.sections WHERE has_age_constraint;


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

SELECT age_source, count(*), count(*)::numeric/(SELECT count(*) proportion FROM macrostrat_api.gbdb_strata_with_age_model) FROM macrostrat_api.gbdb_strata_with_age_model GROUP BY age_source;

SELECT * FROM macrostrat_api.gbdb_formations WHERE formation ILIKE '%Fangyan%';

SELECT * FROM macrostrat_api.gbdb_formations WHERE min_ma IS null ORDER BY formation;

SELECT count(*), round(count(*)::numeric/(SELECT count(*) proportion FROM macrostrat_api.gbdb_strata), 2) FROM macrostrat_api.gbdb_strata WHERE min_ma IS NOT NULL AND max_ma IS NOT NULL;


SELECT age_source, count(*), round(count(*)::numeric/(SELECT count(*) FROM macrostrat_gbdb.strata), 2) proportion FROM macrostrat_api.gbdb_strata_with_age_model WHERE country = 'China' GROUP BY age_source ;

-- Age control

SELECT DISTINCT ON (name_clean) * FROM macrostrat_gbdb.external_age_control;
