import csv
import sys, os
import psycopg2
from psycopg2.extensions import AsIs

# Connect to the database
try:
  conn = psycopg2.connect(dbname="burwell", user="john", host="localhost", port="5432")
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

# Create a cursor
cur = conn.cursor()

def update_lookup(strat_name_id, unit_link) :
    # update lookup table
    cur.execute("""
        UPDATE lookup_%(scale)s a
          SET unit_ids = sub.unit_ids,
              strat_name_ids = sub.strat_name_ids,
              best_age_top = sub.best_age_top,
              best_age_bottom = sub.best_age_bottom,
              color = sub.color
          FROM (
            WITH first as (
                SELECT
                  st.map_id,
                  st.source_id,
                  array(
                    select distinct unit_id
                    FROM maps.map_units m
                    WHERE st.map_id = m.map_id
                    AND basis_col = 'manual'
                  ) AS unit_ids,

                  array(
                    SELECT DISTINCT strat_name_id
                    FROM maps.map_strat_names m
                    WHERE st.map_id = m.map_id
                    AND basis_col = 'manual'
                  ) AS strat_name_ids,

                  t_interval,
                  b_interval
                FROM maps.%(scale)s st
                LEFT JOIN maps.map_units mu ON mu.map_id = st.map_id
                LEFT JOIN maps.map_strat_names msn ON msn.map_id = st.map_id
                WHERE st.map_id IN (
                    SELECT m.map_id
                    FROM maps.medium m
                    JOIN sources.gmus g ON m.orig_id = g.gid
                    WHERE g.unit_link = %(unit_link)s
                )
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

                  ti.age_top,
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
                SELECT
                 map_id,
                 unit_ids,
                 strat_name_ids,
                 best_age_top,
                 best_age_bottom,
                 (SELECT interval_color
                  FROM macrostrat.intervals
                  WHERE age_top <= best_age_top AND age_bottom >= best_age_bottom
                  ORDER BY age_bottom - age_top
                  LIMIT 1
                 ) AS color
                 FROM third
          ) sub
          WHERE a.map_id = sub.map_id
    """, {
        "scale": AsIs("medium"),
        "strat_name_id": strat_name_id,
        "unit_link": unit_link
    })
    conn.commit()


# Read in the csv with the alterations
with open("gmus_alterations.csv") as incsv:
    reader = csv.DictReader(incsv)
    for row in reader:
        print row
        if row["addition"] == 'TRUE':
            # If row['addition'] is true, insert new rows into maps.map_strat_names
            cur.execute("""
                INSERT INTO maps.map_strat_names (map_id, strat_name_id, basis_col) (
                  WITH units AS (
                    SELECT us.unit_id AS unit_id, lsn.strat_name_id, lsn.fm_name AS strat_name, c.poly_geom
                    FROM macrostrat.units_sections us
                    JOIN macrostrat.unit_strat_names usn ON us.unit_id = usn.unit_id
                    JOIN macrostrat.lookup_strat_names lsn ON usn.strat_name_id = lsn.strat_name_id
                    JOIN macrostrat.cols c ON us.col_id = c.id
                    WHERE c.status_code = 'active' AND (lsn.bed_id IN (%(strat_name_id)s) OR lsn.mbr_id IN (%(strat_name_id)s) OR lsn.fm_id IN (%(strat_name_id)s) OR lsn.gp_id IN (%(strat_name_id)s) OR lsn.sgp_id IN (%(strat_name_id)s))
                  ),
                  distance AS (
                    SELECT a.map_id, ST_Distance(a.geom::geography, u.poly_geom::geography)/1000 AS distance, u.unit_id, u.strat_name_id
                    FROM maps.%(scale)s a, units u
                    WHERE map_id IN (
                      SELECT m.map_id
                      FROM maps.medium m
                      JOIN sources.gmus g ON m.orig_id = g.gid
                      WHERE g.unit_link = %(unit_link)s
                    )
                    ORDER BY map_id, distance
                  ),
                  min_dist AS (
                    SELECT map_id, min(distance) AS distance from distance GROUP BY map_id ORDER BY map_id
                  )
                  SELECT distance.map_id, strat_name_id, 'manual' AS type
                  FROM distance
                  JOIN min_dist ON distance.map_id = min_dist.map_id
                  WHERE distance.distance = min_dist.distance
                )
            """, {
                "scale": AsIs("medium"),
                "strat_name_id": row["strat_name_id"],
                "unit_link": row["unit_link"]
            })
            cur.execute("""
                INSERT INTO maps.map_units (map_id, unit_id, basis_col) (
                  WITH units AS (
                    SELECT us.unit_id AS unit_id, lsn.strat_name_id, lsn.fm_name AS strat_name, c.poly_geom
                    FROM macrostrat.units_sections us
                    JOIN macrostrat.unit_strat_names usn ON us.unit_id = usn.unit_id
                    JOIN macrostrat.lookup_strat_names lsn ON usn.strat_name_id = lsn.strat_name_id
                    JOIN macrostrat.cols c ON us.col_id = c.id
                    WHERE c.status_code = 'active' AND (lsn.bed_id IN (%(strat_name_id)s) OR lsn.mbr_id IN (%(strat_name_id)s) OR lsn.fm_id IN (%(strat_name_id)s) OR lsn.gp_id IN (%(strat_name_id)s) OR lsn.sgp_id IN (%(strat_name_id)s))
                  ),
                  distance AS (
                    SELECT a.map_id, ST_Distance(a.geom::geography, u.poly_geom::geography)/1000 AS distance, u.unit_id, u.strat_name_id
                    FROM maps.%(scale)s a, units u
                    WHERE map_id IN (
                      SELECT m.map_id
                      FROM maps.medium m
                      JOIN sources.gmus g ON m.orig_id = g.gid
                      WHERE g.unit_link = %(unit_link)s
                    )
                    ORDER BY map_id, distance
                  ),
                  min_dist AS (
                    SELECT map_id, min(distance) AS distance from distance GROUP BY map_id ORDER BY map_id
                  )
                  SELECT distance.map_id, distance.unit_id, 'manual' AS type
                  FROM distance
                  JOIN min_dist ON distance.map_id = min_dist.map_id
                  WHERE distance.distance = min_dist.distance
                )
            """, {
                "scale": AsIs("medium"),
                "strat_name_id": row["strat_name_id"],
                "unit_link": row["unit_link"]
            })

        # If row['removal'] is true, remove rows from maps.map_strat_names
        else:
            cur.execute("""
                DELETE FROM maps.map_strat_names
                WHERE map_id IN (
                    SELECT m.map_id
                    FROM maps.medium m
                    JOIN sources.gmus g ON m.orig_id = g.gid
                    WHERE g.unit_link = %(unit_link)s
                ) AND strat_name_id = %(strat_name_id)s
            """, {
                "unit_link": row["unit_link"],
                "strat_name_id": row["strat_name_id"]
            })

        conn.commit()
        # update lookup table
        update_lookup(row["strat_name_id"], row["unit_link"])
