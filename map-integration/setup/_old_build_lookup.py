import psycopg2
from psycopg2.extensions import AsIs
import sys, os
import argparse
import time

parser = argparse.ArgumentParser(
  description="Refresh lookup tables",
  epilog="Example usage: python build_lookup.py medium")

parser.add_argument(dest="refresh",
  type=str, nargs=1,
  help="The scale to refresh. If new sources were added or matches were made, make sure to refresh. Can be 'tiny', 'small', 'medium', 'large', or 'all'. Default will not refresh anything.")

arguments = parser.parse_args()

# Connect to the database
try:
  conn = psycopg2.connect(dbname="burwell", user="john", host="localhost", port="5432")
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

cur = conn.cursor()

valid_scales = ["small", "medium", "large", "tiny"]

query = """

CREATE TABLE lookup_%(scale)s_new AS
-- Produce a list of sources and their extents
WITH start AS (
  SELECT source_id, st_extent(geom)::geometry extent
  FROM maps.%(scale)s
  GROUP BY source_id
),
-- Produce a pairwise comparison of sources and whether their extents intersect
list AS (
  SELECT a.source_id s1, b.source_id s2, st_intersects(a.extent, b.extent) intersects
  FROM start a, start b
  ORDER BY a.source_id
),
-- Filter the results of the previous query, finding all intersections
relationships AS (
  select s1, s2 FROM list WHERE intersects IS true
),
-- For each source, create an array of other sources that it touches
summary AS (
  SELECT s1 AS name, array_agg(s2) AS touches
  FROM relationships
  GROUP BY s1
),
-- Sort the above results
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
-- Create a unique group_id for each group of sources
organized AS (
  SELECT DISTINCT my_group, row_number() over() as group_id
  FROM grouped
  GROUP BY my_group
),
-- Make the above result easier to join
parsed AS (
  SELECT unnest(my_group) AS source_id, group_id FROM organized
),

-- Move on to actually assembling the best data
-- First create arrays of the best units and strat_names
first as (
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
  b_interval
FROM maps.%(scale)s st
LEFT JOIN maps.map_units mu ON mu.map_id = st.map_id
LEFT JOIN maps.map_strat_names msn ON msn.map_id = st.map_id
GROUP BY st.map_id
),
-- Get the min t_age and max b_age
second AS (SELECT
  map_id,
  source_id,
  unit_ids,
  strat_name_ids,
  t_interval,
  b_interval,
  (SELECT min(t_age) AS t_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) t_age,
  (SELECT max(b_age) AS b_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) b_age
  FROM first
),
-- Determine the best_age_top and best_age_bottom
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
  END best_age_bottom

 FROM second
 JOIN macrostrat.intervals ti ON ti.id = t_interval
 JOIN macrostrat.intervals tb ON tb.id = b_interval
)
-- Assign a color for making tiles
SELECT map_id,
 group_id,
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
 ) AS color
 FROM third
 JOIN parsed ON parsed.source_id = third.source_id;

CREATE INDEX ON lookup_%(scale)s_new (map_id);
CREATE INDEX ON lookup_%(scale)s_new (group_id);

DROP TABLE IF EXISTS lookup_%(scale)s;
ALTER TABLE lookup_%(scale)s_new RENAME TO lookup_%(scale)s;
"""

def refresh_lookup(scale):
    print "---      ", scale, "       ---"
    start_time = time.time()
    cur.execute(query, {"scale": AsIs(scale)})
    conn.commit()
    conn.set_isolation_level(0)
    cur.execute("VACUUM ANALYZE lookup_%(scale)s;", {"scale": AsIs(scale)})
    conn.commit()
    stop_time = int(time.time() - start_time)
    print "Execution time - ", (stop_time / 60), " minutes and ", (stop_time % 60), " seconds"


if len(arguments.refresh) == 1:
    if arguments.refresh[0] in valid_scales:
        refresh_lookup(arguments.refresh[0])

    elif arguments.refresh[0] == "all":
        for scale in valid_scales:
            refresh_lookup(scale)

    else:
        print "Invalid scale provided..."
