drop materialized view if exists medium_map;
drop materialized view if exists large_map;
drop materialized view if exists small_map;

DROP AGGREGATE IF EXISTS array_agg_mult (anyarray);
CREATE AGGREGATE array_agg_mult (anyarray)  (
    SFUNC     = array_cat
   ,STYPE     = anyarray
   ,INITCOND  = '{}'
);

----------------------------------------------------
---------------------- medium ----------------------
----------------------------------------------------

CREATE MATERIALIZED VIEW medium_map AS

WITH first as (
SELECT
  st.map_id,
  st.source_id,
  array(
  	select distinct unit_id
  	FROM maps.map_units m
  	WHERE st.map_id = m.map_id
  	AND basis_col =
  	  CASE
  	    WHEN 'strat_name' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
  	      'strat_name'
  	    WHEN 'name' in (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
  	      'name'
  	    WHEN 'descrip' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
  	      'descrip'
  	    ELSE
  	     'comments'
  	   END
  ) AS unit_ids,

  array(
  	SELECT DISTINCT strat_name_id
  	FROM maps.map_strat_names m
  	WHERE st.map_id = m.map_id
  	AND basis_col =
  	  CASE
  	    WHEN 'strat_name' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
  	      'strat_name'
  	    WHEN 'name' in (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
  	      'name'
  	    WHEN 'descrip' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
  	      'descrip'
  	    ELSE
  	     'comments'
  	   END
  ) AS strat_name_ids,

  t_interval,
  b_interval,
  geom
FROM maps.medium st
LEFT JOIN maps.map_units mu ON mu.map_id = st.map_id
LEFT JOIN maps.map_strat_names msn ON msn.map_id = st.map_id
GROUP BY st.map_id
),
second AS (SELECT
  map_id,
  source_id,
  unit_ids,
  strat_name_ids,
  t_interval,
  b_interval,
  (SELECT min(t_age) AS t_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) t_age,
  (SELECT max(b_age) AS b_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) b_age,
  geom
  FROM first
),

third AS (

SELECT map_id,
  source_id,
  unit_ids,
  strat_name_ids,

  ti.interval_name AS t_interval_name,
  ti.age_top,

  tb.interval_name AS b_interval_name,
  tb.age_bottom,

  t_age,
  b_age,

  CASE
  	WHEN t_age IS NULL THEN
  	  ti.age_top
  	 ELSE
  	   t_age
  END best_age_top,

  CASE
  	WHEN b_age IS NULL THEN
  	  tb.age_bottom
  	 ELSE
  	   b_age
  END best_age_bottom,

  geom

 FROM second
 JOIN macrostrat.intervals ti ON ti.id = t_interval
 JOIN macrostrat.intervals tb ON tb.id = b_interval
)

 SELECT map_id,
  source_id,
  unit_ids,
  strat_name_ids,

  t_interval_name,
  b_interval_name,

  age_top AS t_age,
  age_bottom AS b_age,

  best_age_top,
  best_age_bottom,

  (SELECT interval_color
   FROM macrostrat.intervals
   WHERE age_top <= best_age_top AND age_bottom >= best_age_bottom
   ORDER BY age_bottom - age_top
   LIMIT 1
  ) AS color,
  geom
  FROM third;



----------------------------------------------------
---------------------- small -----------------------
----------------------------------------------------


CREATE MATERIALIZED VIEW small_map AS
WITH first as (
SELECT
  st.map_id,
  st.source_id,
  array(
  	select distinct unit_id
  	FROM maps.map_units m
  	WHERE st.map_id = m.map_id
  	AND basis_col =
  	  CASE
  	    WHEN 'strat_name' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
  	      'strat_name'
  	    WHEN 'name' in (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
  	      'name'
  	    WHEN 'descrip' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
  	      'descrip'
  	    ELSE
  	     'comments'
  	   END
  ) AS unit_ids,

  array(
  	SELECT DISTINCT strat_name_id
  	FROM maps.map_strat_names m
  	WHERE st.map_id = m.map_id
  	AND basis_col =
  	  CASE
  	    WHEN 'strat_name' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
  	      'strat_name'
  	    WHEN 'name' in (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
  	      'name'
  	    WHEN 'descrip' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
  	      'descrip'
  	    ELSE
  	     'comments'
  	   END
  ) AS strat_name_ids,

  t_interval,
  b_interval,
  geom
FROM maps.small st
LEFT JOIN maps.map_units mu ON mu.map_id = st.map_id
LEFT JOIN maps.map_strat_names msn ON msn.map_id = st.map_id
GROUP BY st.map_id
),
second AS (SELECT
  map_id,
  source_id,
  unit_ids,
  strat_name_ids,
  t_interval,
  b_interval,
  (SELECT min(t_age) AS t_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) t_age,
  (SELECT max(b_age) AS b_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) b_age,
  geom
  FROM first
),

third AS (

SELECT map_id,
  source_id,
  unit_ids,
  strat_name_ids,

  ti.interval_name AS t_interval_name,
  ti.age_top,

  tb.interval_name AS b_interval_name,
  tb.age_bottom,

  t_age,
  b_age,

  CASE
  	WHEN t_age IS NULL THEN
  	  ti.age_top
  	 ELSE
  	   t_age
  END best_age_top,

  CASE
  	WHEN b_age IS NULL THEN
  	  tb.age_bottom
  	 ELSE
  	   b_age
  END best_age_bottom,

  geom

 FROM second
 JOIN macrostrat.intervals ti ON ti.id = t_interval
 JOIN macrostrat.intervals tb ON tb.id = b_interval
)

 SELECT map_id,
  source_id,
  unit_ids,
  strat_name_ids,

  t_interval_name,
  b_interval_name,

  age_top AS t_age,
  age_bottom AS b_age,

  best_age_top,
  best_age_bottom,

  (SELECT interval_color
   FROM macrostrat.intervals
   WHERE age_top <= best_age_top AND age_bottom >= best_age_bottom
   ORDER BY age_bottom - age_top
   LIMIT 1
  ) AS color,
  geom
  FROM third;


----------------------------------------------------
---------------------- large -----------------------
----------------------------------------------------

CREATE MATERIALIZED VIEW large_map AS

WITH first as (
SELECT
  st.map_id,
  st.source_id,
  array(
  	select distinct unit_id
  	FROM maps.map_units m
  	WHERE st.map_id = m.map_id
  	AND basis_col =
  	  CASE
  	    WHEN 'strat_name' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
  	      'strat_name'
  	    WHEN 'name' in (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
  	      'name'
  	    WHEN 'descrip' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
  	      'descrip'
  	    ELSE
  	     'comments'
  	   END
  ) AS unit_ids,

  array(
  	SELECT DISTINCT strat_name_id
  	FROM maps.map_strat_names m
  	WHERE st.map_id = m.map_id
  	AND basis_col =
  	  CASE
  	    WHEN 'strat_name' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
  	      'strat_name'
  	    WHEN 'name' in (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
  	      'name'
  	    WHEN 'descrip' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
  	      'descrip'
  	    ELSE
  	     'comments'
  	   END
  ) AS strat_name_ids,

  t_interval,
  b_interval,
  geom
FROM maps.large st
LEFT JOIN maps.map_units mu ON mu.map_id = st.map_id
LEFT JOIN maps.map_strat_names msn ON msn.map_id = st.map_id
GROUP BY st.map_id
),
second AS (SELECT
  map_id,
  source_id,
  unit_ids,
  strat_name_ids,
  t_interval,
  b_interval,
  (SELECT min(t_age) AS t_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) t_age,
  (SELECT max(b_age) AS b_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) b_age,
  geom
  FROM first
),

third AS (

SELECT map_id,
  source_id,
  unit_ids,
  strat_name_ids,

  ti.interval_name AS t_interval_name,
  ti.age_top,

  tb.interval_name AS b_interval_name,
  tb.age_bottom,

  t_age,
  b_age,

  CASE
  	WHEN t_age IS NULL THEN
  	  ti.age_top
  	 ELSE
  	   t_age
  END best_age_top,

  CASE
  	WHEN b_age IS NULL THEN
  	  tb.age_bottom
  	 ELSE
  	   b_age
  END best_age_bottom,

  geom

 FROM second
 JOIN macrostrat.intervals ti ON ti.id = t_interval
 JOIN macrostrat.intervals tb ON tb.id = b_interval
)

 SELECT map_id,
  source_id,
  unit_ids,
  strat_name_ids,

  t_interval_name,
  b_interval_name,

  age_top AS t_age,
  age_bottom AS b_age,

  best_age_top,
  best_age_bottom,

  (SELECT interval_color
   FROM macrostrat.intervals
   WHERE age_top <= best_age_top AND age_bottom >= best_age_bottom
   ORDER BY age_bottom - age_top
   LIMIT 1
  ) AS color,
  geom
  FROM third;


CREATE INDEX medium_map_map_idx ON medium_map (map_id);
CREATE INDEX medium_map_source_idx ON medium_map (source_id);
CREATE INDEX medium_map_geom_idx ON medium_map USING GIST (geom);

CREATE INDEX small_map_map_idx ON small_map (map_id);
CREATE INDEX small_map_source_idx ON small_map (source_id);
CREATE INDEX small_map_geom_idx ON small_map USING GIST (geom);

CREATE INDEX large_map_map_idx ON large_map (map_id);
CREATE INDEX large_map_source_idx ON large_map (source_id);
CREATE INDEX large_map_geom_idx ON large_map USING GIST (geom);
