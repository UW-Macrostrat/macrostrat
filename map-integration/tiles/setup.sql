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
WITH start AS (
	SELECT source_id, st_extent(geom)::geometry extent
	FROM maps.medium
	GROUP BY source_id
),
list AS (
	SELECT a.source_id s1, b.source_id s2, st_intersects(a.extent, b.extent) intersects
	FROM start a, start b
	ORDER BY a.source_id
),
relationships AS (
	select s1, s2 FROM list WHERE intersects IS true
),
summary AS (
	SELECT s1 AS name, array_agg(s2) AS touches
	FROM relationships
	GROUP BY s1
),
grouped AS (
	SELECT name as source_id, (
		SELECT array_agg(uniques) FROM (
			select distinct unnest(array_agg_mult(sub.touches)) AS uniques
			ORDER BY uniques
		) x
	) my_group

	FROM summary LEFT JOIN LATERAL (
	  SELECT touches
	  FROM summary r
	  WHERE summary.touches && r.touches
	  GROUP BY name, touches
	) sub ON true
	GROUP BY summary.name
	ORDER BY summary.name
),

organized AS (
  SELECT DISTINCT my_group, row_number() over() as group_id
  FROM grouped
  GROUP BY my_group
),

parsed AS (
  SELECT unnest(my_group) AS source_id, group_id FROM organized
)

SELECT
  map_id,
  medium.source_id,
  geom,
  (select interval_color from macrostrat.intervals where age_top <= ti.age_top AND age_bottom >= tb.age_bottom order by age_bottom - age_top limit 1) color,
  group_id
FROM maps.medium
JOIN macrostrat.intervals ti ON ti.id = t_interval
JOIN macrostrat.intervals tb ON tb.id = b_interval
JOIN parsed ON parsed.source_id = medium.source_id;



----------------------------------------------------
---------------------- small -----------------------
----------------------------------------------------


CREATE MATERIALIZED VIEW small_map AS
WITH start AS (
	SELECT source_id, st_extent(geom)::geometry extent
	FROM maps.small
	GROUP BY source_id
),

list AS (
	SELECT a.source_id s1, b.source_id s2, st_intersects(a.extent, b.extent) intersects
	FROM start a, start b
	ORDER BY a.source_id
),

relationships AS (
	select s1, s2 FROM list WHERE intersects IS true
),

summary AS (
	SELECT s1 AS name, array_agg(s2) AS touches
	FROM relationships
	GROUP BY s1
),

grouped AS (
	SELECT name as source_id, (
		SELECT array_agg(uniques) FROM (
			select distinct unnest(array_agg_mult(sub.touches)) AS uniques
			ORDER BY uniques
		) x
	) my_group

	FROM summary LEFT JOIN LATERAL (
	  SELECT touches
	  FROM summary r
	  WHERE summary.touches && r.touches
	  GROUP BY name, touches
	) sub ON true
	GROUP BY summary.name
	ORDER BY summary.name
),

organized AS (
  SELECT DISTINCT my_group, row_number() over() as group_id
  FROM grouped
  GROUP BY my_group
),

parsed AS (
  SELECT unnest(my_group) AS source_id, group_id FROM organized
)

SELECT
  map_id,
  small.source_id,
  geom,
  (select interval_color from macrostrat.intervals where age_top <= ti.age_top AND age_bottom >= tb.age_bottom order by age_bottom - age_top limit 1) color,
  group_id
FROM maps.small
JOIN macrostrat.intervals ti ON ti.id = t_interval
JOIN macrostrat.intervals tb ON tb.id = b_interval
JOIN parsed ON parsed.source_id = small.source_id;




----------------------------------------------------
---------------------- large -----------------------
----------------------------------------------------

CREATE MATERIALIZED VIEW large_map AS
WITH start AS (
	SELECT source_id, st_extent(geom)::geometry extent
	FROM maps.large
	GROUP BY source_id
),

list AS (
	SELECT a.source_id s1, b.source_id s2, st_intersects(a.extent, b.extent) intersects
	FROM start a, start b
	ORDER BY a.source_id
),

relationships AS (
	select s1, s2 FROM list WHERE intersects IS true
),

summary AS (
	SELECT s1 AS name, array_agg(s2) AS touches
	FROM relationships
	GROUP BY s1
),

grouped AS (
	SELECT name as source_id, (
		SELECT array_agg(uniques) FROM (
			select distinct unnest(array_agg_mult(sub.touches)) AS uniques
			ORDER BY uniques
		) x
	) my_group

	FROM summary LEFT JOIN LATERAL (
	  SELECT touches
	  FROM summary r
	  WHERE summary.touches && r.touches
	  GROUP BY name, touches
	) sub ON true
	GROUP BY summary.name
	ORDER BY summary.name
),

organized AS (
  SELECT DISTINCT my_group, row_number() over() as group_id
  FROM grouped
  GROUP BY my_group
),

parsed AS (
  SELECT unnest(my_group) AS source_id, group_id FROM organized
)

SELECT
  map_id,
  large.source_id,
  geom,
  (select interval_color from macrostrat.intervals where age_top <= ti.age_top AND age_bottom >= tb.age_bottom order by age_bottom - age_top limit 1) color,
  group_id
FROM maps.large
JOIN macrostrat.intervals ti ON ti.id = t_interval
JOIN macrostrat.intervals tb ON tb.id = b_interval
JOIN parsed ON parsed.source_id = large.source_id;



CREATE INDEX medium_map_map_idx ON medium_map (map_id);
CREATE INDEX medium_map_source_idx ON medium_map (source_id);
CREATE INDEX medium_map_geom_idx ON medium_map USING GIST (geom);

CREATE INDEX small_map_map_idx ON small_map (map_id);
CREATE INDEX small_map_source_idx ON small_map (source_id);
CREATE INDEX small_map_geom_idx ON small_map USING GIST (geom);

CREATE INDEX large_map_map_idx ON large_map (map_id);
CREATE INDEX large_map_source_idx ON large_map (source_id);
CREATE INDEX large_map_geom_idx ON large_map USING GIST (geom);
