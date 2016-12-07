import argparse
import sys, os
import psycopg2
from psycopg2.extensions import AsIs
import yaml

with open(os.path.join(os.path.dirname(__file__), '../credentials.yml'), 'r') as f:
    credentials = yaml.load(f)

parser = argparse.ArgumentParser(
  description="Manually remove strat_name_id or unit_id matches with Burwell map_ids",
  epilog="python remove_match.py --map_id 12345 --strat_name_id 9876")

parser.add_argument("-m", "--map_id", dest="map_id",
  default="na", type=str, required=True,
  help="Burwell map_id")

parser.add_argument("-sn", "--strat_name_id", dest="strat_name_id",
  default="na", type=str, required=False,
  help="Macrostrat strat_name_id")

parser.add_argument("-u", "--unit_id", dest="unit_id",
  default="na", type=str, required=False,
  help="Macrostrat unit_id")

parser.add_argument("-i", "--identical", dest="identical_field",
  default="na", type=str, required=False,
  help="Apply removal to all polygons with an identical given field. Example: -i strat_name.")

arguments = parser.parse_args()

if (arguments.unit_id == "na" and arguments.strat_name_id == "na") or (arguments.unit_id != "na" and arguments.strat_name_id != "na") :
  print "Unit or strat_name_id parameter required, but not both"
  sys.exit()

# Connect to the database
try:
  conn = psycopg2.connect(dbname=credentials["pg_db"], user=credentials["pg_user"], host=credentials["pg_host"], port=credentials["pg_port"])
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
        	UNION ALL
        	SELECT map_id, source_id FROM maps.medium
        	UNION ALL
        	SELECT map_id, source_id FROM maps.small
        ) a) sub
        JOIN maps.sources s ON sub.source_id = s.source_id
        where map_id = %(map_id)s
    """, {"map_id": map_id})

    return cur.fetchone()[0]


def update_lookup(scale, map_id) :
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
                    AND basis_col = ANY(CASE
                      WHEN 'manual_replace' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
                        array['manual_replace']
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
                  ) AS unit_ids,

                  array(
                    SELECT DISTINCT strat_name_id
                    FROM maps.map_strat_names m
                    WHERE st.map_id = m.map_id
                    AND basis_col = ANY(CASE
                      WHEN 'manual_replace' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
                        array['manual_replace']
                      WHEN 'strat_name' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
                        array['strat_name', 'manual']
                      WHEN 'name' in (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
                        array['name', 'manual']
                      WHEN 'descrip' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
                        array['descrip', 'manual']
                      WHEN 'comments' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
                        array['comments', 'manual']
                      WHEN 'strat_name_buffer' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
                        array['strat_name_buffer', 'manual']
                      WHEN 'name_buffer' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
                        array['name_buffer', 'manual']
                      WHEN 'descrip' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
                        array['descrip', 'manual']
                      WHEN 'comments_buffer' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
                        array['comments_buffer', 'manual']
                      ELSE
                       array['unknown', 'manual']
                     END)
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


def remove_unit() :
    # Get scale of this map_id
    scale = get_scale(arguments.map_id)

    # Delete from maps.map_units
    cur.execute("""
        DELETE FROM maps.map_units
        WHERE map_id IN (
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
        )
        AND unit_id = %(unit_id)s
        AND (basis_col = 'manual' OR basis_col = 'manual_replace')
    """, {
        "scale": AsIs(scale),
        "map_id": arguments.map_id,
        "unit_id": arguments.unit_id
    })

    # Insert into maps.map_strat_names
    cur.execute("""
        DELETE FROM maps.map_strat_names
        WHERE map_id IN (
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
        )
        AND strat_name_id IN (
            SELECT strat_name_id
            FROM macrostrat.unit_strat_names
            WHERE unit_id = %(unit_id)s
        )
        AND (basis_col = 'manual' OR basis_col = 'manual_replace')
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

        INSERT INTO maps.manual_matches (map_id, unit_id, removal) VALUES (%(map_id)s, %(unit_id)s, TRUE);
    """, {
        "unit_id": arguments.unit_id,
        "map_id": arguments.map_id
    })
    conn.commit()




def remove_strat_name() :
    # First get scale of this map_id
    scale = get_scale(arguments.map_id)

    # Delete matches from maps.map_strat_names
    cur.execute("""
        DELETE FROM maps.map_strat_names
        WHERE map_id IN (
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
        )
        AND strat_name_id = %(strat_name_id)s
        AND (basis_col = 'manual' OR basis_col = 'manual_replace')
    """, {
        "scale": AsIs(scale),
        "strat_name_id": arguments.strat_name_id,
        "map_id": arguments.map_id
    })

    # Insert new matches into maps.map_units
    cur.execute("""
        DELETE FROM maps.map_units
        WHERE map_id IN (
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
        )
        AND unit_id IN (
            SELECT us.unit_id
            FROM macrostrat.units_sections us
            JOIN macrostrat.unit_strat_names usn ON us.unit_id = usn.unit_id
            JOIN macrostrat.lookup_strat_names lsn ON usn.strat_name_id = lsn.strat_name_id
            WHERE (lsn.bed_id IN (%(strat_name_id)s) OR lsn.mbr_id IN (%(strat_name_id)s) OR lsn.fm_id IN (%(strat_name_id)s) OR lsn.gp_id IN (%(strat_name_id)s) OR lsn.sgp_id IN (%(strat_name_id)s))
        )
        AND (basis_col = 'manual' OR basis_col = 'manual_replace')
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

        INSERT INTO maps.manual_matches (map_id, strat_name_id, removal) VALUES (%(map_id)s, %(strat_name_id)s, TRUE);
    """, {
        "strat_name_id": arguments.strat_name_id,
        "map_id": arguments.map_id
    })
    conn.commit()





# Do a strat_name_id match
if arguments.strat_name_id != "na":
    remove_strat_name()

elif arguments.unit_id != "na":
    remove_unit()

else:
    print "You should never see this message"
