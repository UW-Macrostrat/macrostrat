import argparse
import sys, os
import psycopg2
from psycopg2.extensions import AsIs

parser = argparse.ArgumentParser(
  description="Manually match a Burwell map_id with a Macrostrat strat_name_id or unit_id",
  epilog="python add_match.py --map_id 12345 --strat_name_id 9876 --type add")

parser.add_argument("-m", "--map_id", dest="map_id",
  default="na", type=str, required=True,
  help="Burwell map_id")

parser.add_argument("-t", "--type", dest="type",
  default="na", type=str, required=True,
  help="Additional type. Can be 'replace' to replace all best matches with a manual match, or 'add' to add the manual match to the existing best matches.")

parser.add_argument("-sn", "--strat_name_id", dest="strat_name_id",
  default="na", type=str, required=False,
  help="Macrostrat strat_name_id")

parser.add_argument("-u", "--unit_id", dest="unit_id",
  default="na", type=str, required=False,
  help="Macrostrat unit_id")

arguments = parser.parse_args()

if (arguments.unit_id == "na" and arguments.strat_name_id == "na") or (arguments.unit_id != "na" and arguments.strat_name_id != "na") :
  print "Unit or strat_name_id parameter required, but not both"
  sys.exit()

if (arguments.type != "replace" and arguments.type != "add") :
    print "Type must be 'replace' or 'add'"
    sys.exit()

# Connect to the database
try:
  conn = psycopg2.connect(dbname="burwell", user="john", host="localhost", port="5432")
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

# Create a cursor
cur = conn.cursor()

def get_scale(map_id) :
    cur.execute("""
        SELECT scale
        FROM (SELECT map_id, source_id FROM (
        	SELECT map_id, source_id FROM maps.large
        	UNION
        	SELECT map_id, source_id FROM maps.medium
        	UNION
        	SELECT map_id, source_id FROM maps.small
        ) a) sub
        JOIN maps.sources s ON sub.source_id = s.source_id
        where map_id = %(map_id)s
    """, {"map_id": map_id})

    return cur.fetchone()[0]


def update_lookup(scale, map_id) :
    if arguments.type == 'replace' :
        basis = "'manual'"
    else :
        basis = """
            ANY(CASE
              WHEN 'strat_name' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
                array['strat_name', 'manual']
              WHEN 'name' in (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
                array['name', 'manual']
              WHEN 'descrip' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
                array['descrip', 'manual']
              WHEN 'comments' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
                array['comments', 'manual']
              WHEN 'strat_name_buffer' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
                array['strat_name_buffer', 'manual']
              WHEN 'name_buffer' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
                array['name_buffer', 'manual']
              WHEN 'descrip' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
                array['descrip', 'manual']
              WHEN 'comments_buffer' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
                array['comments_buffer', 'manual']
              ELSE
               array['unknown', 'manual']
             END)
        """

    # Update lookup table
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
                    AND basis_col = """ + basis + """
                  ) AS unit_ids,

                  array(
                    SELECT DISTINCT strat_name_id
                    FROM maps.map_strat_names m
                    WHERE st.map_id = m.map_id
                    AND basis_col = """ + basis + """
                  ) AS strat_name_ids,

                  t_interval,
                  b_interval
                FROM maps.%(scale)s st
                LEFT JOIN maps.map_units mu ON mu.map_id = st.map_id
                LEFT JOIN maps.map_strat_names msn ON msn.map_id = st.map_id
                WHERE st.map_id = %(map_id)s
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
        "scale": AsIs(scale),
        "map_id": arguments.map_id
    })
    conn.commit()


def unit_match() :
    # Get scale of this map_id
    scale = get_scale(arguments.map_id)

    # Verify that this unit_id has only one strat_name_id attached to it
    cur.execute("""
        WITH sub AS (SELECT unit_id, count(*) a FROM macrostrat.unit_strat_names
          WHERE unit_id = %(unit_id)s
          GROUP BY unit_id)
        select * from sub where a > 1 order by a desc LIMIT 1
    """, {"unit_id": arguments.unit_id})
    unit_names = cur.fetchall()

    # If it has more than one strat_name_id, exit
    if len(unit_names) > 0:
        print "Sorry, this unit_id has more than one strat name assigned to it"
        sys.exit()

    print arguments.map_id
    # Insert into maps.map_units
    cur.execute("""
        INSERT INTO maps.map_units (map_id, unit_id, basis_col) (
            SELECT map_id, %(unit_id)s AS unit_id, 'manual'
            FROM maps.%(scale)s
            WHERE source_id = (SELECT source_id FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND name IS NOT DISTINCT FROM (SELECT name FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND strat_name IS NOT DISTINCT FROM (SELECT strat_name FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND age IS NOT DISTINCT FROM (SELECT age FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND lith IS NOT DISTINCT FROM (SELECT lith FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND descrip IS NOT DISTINCT FROM (SELECT descrip FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND comments IS NOT DISTINCT FROM (SELECT comments FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND t_interval IS NOT DISTINCT FROM (SELECT t_interval FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND b_interval IS NOT DISTINCT FROM (SELECT b_interval FROM maps.%(scale)s WHERE map_id = %(map_id)s)
        )
    """, {
        "scale": AsIs(scale),
        "map_id": arguments.map_id,
        "unit_id": arguments.unit_id
    })

    # Insert into maps.map_strat_names
    cur.execute("""
        INSERT INTO maps.map_strat_names (map_id, strat_name_id, basis_col) (
            SELECT map_id, (
                SELECT strat_name_id
                FROM macrostrat.unit_strat_names
                WHERE unit_id = %(unit_id)s
            ) AS strat_name_id, 'manual' AS basis_col
            FROM maps.%(scale)s
            WHERE source_id = (SELECT source_id FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND name IS NOT DISTINCT FROM (SELECT name FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND strat_name IS NOT DISTINCT FROM (SELECT strat_name FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND age IS NOT DISTINCT FROM (SELECT age FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND lith IS NOT DISTINCT FROM (SELECT lith FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND descrip IS NOT DISTINCT FROM (SELECT descrip FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND comments IS NOT DISTINCT FROM (SELECT comments FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND t_interval IS NOT DISTINCT FROM (SELECT t_interval FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND b_interval IS NOT DISTINCT FROM (SELECT b_interval FROM maps.%(scale)s WHERE map_id = %(map_id)s)
        )
    """, {
        "scale": AsIs(scale),
        "map_id": arguments.map_id,
        "unit_id": arguments.unit_id
    })
    conn.commit()

    # Update lookup table
    update_lookup(scale, arguments.map_id)

    # Update alterations table
    cur.execute("""
        DELETE FROM maps.manual_matches
        WHERE map_id = %(map_id)s
        AND unit_id = %(unit_id)s;

        INSERT INTO maps.manual_matches (map_id, unit_id, addition) VALUES (%(map_id)s, %(unit_id)s, TRUE);
    """, {
        "unit_id": arguments.unit_id,
        "map_id": arguments.map_id
    })
    conn.commit()




def strat_name_match() :
    # First get scale of this map_id
    scale = get_scale(arguments.map_id)

    # Insert new matches in maps.map_strat_names
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
          concepts AS (
            SELECT map_id
            FROM maps.%(scale)s
            WHERE source_id = (SELECT source_id FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND name IS NOT DISTINCT FROM (SELECT name FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND strat_name IS NOT DISTINCT FROM (SELECT strat_name FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND age IS NOT DISTINCT FROM (SELECT age FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND lith IS NOT DISTINCT FROM (SELECT lith FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND descrip IS NOT DISTINCT FROM (SELECT descrip FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND comments IS NOT DISTINCT FROM (SELECT comments FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND t_interval IS NOT DISTINCT FROM (SELECT t_interval FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND b_interval IS NOT DISTINCT FROM (SELECT b_interval FROM maps.%(scale)s WHERE map_id = %(map_id)s)
          ),
          distance AS (
            SELECT a.map_id, ST_Distance(a.geom::geography, u.poly_geom::geography)/1000 AS distance, u.unit_id, u.strat_name_id
            FROM maps.%(scale)s a, units u
            WHERE map_id IN (
                SELECT * FROM concepts
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
        "scale": AsIs(scale),
        "strat_name_id": arguments.strat_name_id,
        "map_id": arguments.map_id
    })

    # Insert new matches into maps.map_units
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
          concepts AS (
            SELECT map_id
            FROM maps.%(scale)s
            WHERE source_id = (SELECT source_id FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND name IS NOT DISTINCT FROM (SELECT name FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND strat_name IS NOT DISTINCT FROM (SELECT strat_name FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND age IS NOT DISTINCT FROM (SELECT age FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND lith IS NOT DISTINCT FROM (SELECT lith FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND descrip IS NOT DISTINCT FROM (SELECT descrip FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND comments IS NOT DISTINCT FROM (SELECT comments FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND t_interval IS NOT DISTINCT FROM (SELECT t_interval FROM maps.%(scale)s WHERE map_id = %(map_id)s)
            AND b_interval IS NOT DISTINCT FROM (SELECT b_interval FROM maps.%(scale)s WHERE map_id = %(map_id)s)
          ),
          distance AS (
            SELECT a.map_id, ST_Distance(a.geom::geography, u.poly_geom::geography)/1000 AS distance, u.unit_id, u.strat_name_id
            FROM maps.%(scale)s a, units u
            WHERE map_id IN (
                SELECT * FROM concepts
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
        "scale": AsIs(scale),
        "strat_name_id": arguments.strat_name_id,
        "map_id": arguments.map_id
    })

    update_lookup(scale, arguments.map_id)

    # Update alterations table
    cur.execute("""
        DELETE FROM maps.manual_matches
        WHERE map_id = %(map_id)s
        AND strat_name_id = %(strat_name_id)s;

        INSERT INTO maps.manual_matches (map_id, strat_name_id, addition) VALUES (%(map_id)s, %(strat_name_id)s, TRUE);
    """, {
        "strat_name_id": arguments.strat_name_id,
        "map_id": arguments.map_id
    })
    conn.commit()





# Do a strat_name_id match
if arguments.strat_name_id != "na":
    strat_name_match()

elif arguments.unit_id != "na":
    unit_match()

else:
    print "You should never see this message"
