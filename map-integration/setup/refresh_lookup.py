import psycopg2
from psycopg2.extensions import AsIs
import sys, os
import argparse
import time
import credentials as creds

parser = argparse.ArgumentParser(
  description="Refresh lookup tables",
  epilog="Example usage: python refresh_lookup.py medium")

parser.add_argument(dest="refresh",
  type=str, nargs=1,
  help="A valid source_id or scale name to refresh. If new sources were added or matches were made, make sure to refresh. Can be any valid source_id, scale name, or 'all'. Default will not refresh anything.")

arguments = parser.parse_args()

# Connect to the database
try:
  conn = psycopg2.connect(dbname=creds.pg_db, user=creds.pg_user, host=creds.pg_host, port=creds.pg_port)
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

cur = conn.cursor()

valid_scales = ["tiny", "small", "medium", "large"]


def find_sources(scale):
    cur.execute("SELECT source_id FROM maps.sources WHERE scale = %(scale)s", {"scale": scale})
    return cur.fetchall()


def find_scale(source_id):
    cur.execute("SELECT scale from maps.sources WHERE source_id = %(source_id)s", {"source_id": source_id})
    result = cur.fetchone()[0]
    return result


def refresh(scale, source_id):
    # Delete source from lookup_scale
    cur.execute("""
    DELETE FROM lookup_%(scale)s
    WHERE map_id IN (
        SELECT map_id
        FROM maps.%(scale)s
        WHERE source_id =  %(source_id)s
    )
    """, {"scale": AsIs(scale), "source_id": source_id})

    # Insert source into lookup_scale
    cur.execute("""
    INSERT INTO lookup_%(scale)s (map_id, unit_ids, strat_name_ids, lith_ids, best_age_top, best_age_bottom, color) (
      -- First create arrays of the best units and strat_names

     WITH unit_bases AS (
       SELECT array_agg(distinct basis_col) bases, q.map_id
       FROM maps.map_units
       JOIN maps.%(scale)s q ON map_units.map_id = q.map_id
       WHERE source_id = %(source_id)s
       GROUP BY q.map_id
       ORDER BY q.map_id
     ),
     unit_ids AS (
       SELECT q.map_id, array_agg(DISTINCT unit_id) AS unit_ids
       FROM maps.%(scale)s q
       JOIN maps.map_units ON q.map_id = map_units.map_id
       JOIN unit_bases ON unit_bases.map_id = q.map_id

       WHERE source_id = %(source_id)s AND map_units.basis_col = ANY(
         CASE
           WHEN 'manual_replace' = ANY(bases)
             THEN array['manual_replace']
         	WHEN 'strat_name' = ANY(bases)
         	  THEN array['strat_name', 'manual']
           WHEN 'name' = ANY(bases)
             THEN array['name', 'manual']
           WHEN 'descrip' = ANY(bases)
             THEN array['descrip', 'manual']
           WHEN 'comments' = ANY(bases)
             THEN array['comments', 'manual']
         	WHEN 'strat_name_buffer' = ANY(bases)
         	  THEN array['strat_name_buffer', 'manual']
           WHEN 'name_buffer' = ANY(bases)
             THEN array['name_buffer', 'manual']
           WHEN 'descrip_buffer' = ANY(bases)
             THEN array['descrip_buffer', 'manual']
           WHEN 'comments_buffer' = ANY(bases)
             THEN array['comments_buffer', 'manual']
         	ELSE
         	  array['unknown', 'manual']
         	END
       )
       GROUP BY q.map_id
     ),
     strat_name_bases AS (
       SELECT array_agg(distinct basis_col) bases, q.map_id
       FROM maps.map_strat_names
       JOIN maps.%(scale)s q ON map_strat_names.map_id = q.map_id
       WHERE source_id = %(source_id)s
       GROUP BY q.map_id
       ORDER BY q.map_id
     ),
     strat_name_ids AS (
       SELECT q.map_id, array_agg(DISTINCT strat_name_id) AS strat_name_ids
       FROM maps.%(scale)s q
       JOIN maps.map_strat_names ON q.map_id = map_strat_names.map_id
       JOIN strat_name_bases ON strat_name_bases.map_id = q.map_id
       WHERE source_id = %(source_id)s AND map_strat_names.basis_col = ANY(
         CASE
           WHEN 'manual_replace' = ANY(bases)
             THEN array['manual_replace']
         	WHEN 'strat_name' = ANY(bases)
         	  THEN array['strat_name', 'manual']
           WHEN 'name' = ANY(bases)
             THEN array['name', 'manual']
           WHEN 'descrip' = ANY(bases)
             THEN array['descrip', 'manual']
           WHEN 'comments' = ANY(bases)
             THEN array['comments', 'manual']
         	WHEN 'strat_name_buffer' = ANY(bases)
         	  THEN array['strat_name_buffer', 'manual']
           WHEN 'name_buffer' = ANY(bases)
             THEN array['name_buffer', 'manual']
           WHEN 'descrip_buffer' = ANY(bases)
             THEN array['descrip_buffer', 'manual']
           WHEN 'comments_buffer' = ANY(bases)
             THEN array['comments_buffer', 'manual']
         	ELSE
         	  array['unknown', 'manual']
         	END
       )
       GROUP BY q.map_id
     ),
     lith_bases AS (
       SELECT array_agg(distinct basis_col) bases, q.map_id
       FROM maps.map_liths
       JOIN maps.%(scale)s q ON map_liths.map_id = q.map_id
       WHERE source_id = %(source_id)s
       GROUP BY q.map_id
       ORDER BY q.map_id
     ),
     lith_ids AS (
       SELECT q.map_id, array_agg(DISTINCT lith_id) AS lith_ids
       FROM maps.%(scale)s q
       JOIN maps.map_liths ON q.map_id = map_liths.map_id
       JOIN lith_bases ON lith_bases.map_id = q.map_id
       WHERE source_id = %(source_id)s AND map_liths.basis_col = ANY(
         CASE
           WHEN 'manual_replace' = ANY(bases)
             THEN array['manual_replace']
         	WHEN 'strat_name' = ANY(bases)
         	  THEN array['strat_name', 'manual']
           WHEN 'name' = ANY(bases)
             THEN array['name', 'manual']
           WHEN 'descrip' = ANY(bases)
             THEN array['descrip', 'manual']
           WHEN 'comments' = ANY(bases)
             THEN array['comments', 'manual']
         	WHEN 'strat_name_buffer' = ANY(bases)
         	  THEN array['strat_name_buffer', 'manual']
           WHEN 'name_buffer' = ANY(bases)
             THEN array['name_buffer', 'manual']
           WHEN 'descrip_buffer' = ANY(bases)
             THEN array['descrip_buffer', 'manual']
           WHEN 'comments_buffer' = ANY(bases)
             THEN array['comments_buffer', 'manual']
         	ELSE
         	  array['unknown', 'manual']
         	END
       )
       GROUP BY q.map_id
     ),
     match_summary AS (
       SELECT
         q.map_id,
         COALESCE(unit_ids.unit_ids, '{}') unit_ids,
         COALESCE(strat_name_ids.strat_name_ids, '{}') strat_name_ids,
         COALESCE(lith_ids.lith_ids, '{}') lith_ids,
         t_interval,
         b_interval
       FROM maps.%(scale)s q
       LEFT JOIN unit_ids ON q.map_id = unit_ids.map_id
       LEFT JOIN strat_name_ids ON q.map_id = strat_name_ids.map_id
       LEFT JOIN lith_ids ON q.map_id = lith_ids.map_id
       WHERE source_id = %(source_id)s
     ),
     macro_ages AS (
       SELECT
         map_id,
         unit_ids,
         strat_name_ids,
         lith_ids,
         t_interval,
         b_interval,

         (SELECT min(t_age) AS t_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) t_age,
         (SELECT max(b_age) AS b_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) b_age
       FROM match_summary
     ),
     -- Determine the best_age_top and best_age_bottom
     best_times AS (
       SELECT
         map_id,
         unit_ids,
         strat_name_ids,
         lith_ids,

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

      FROM macro_ages
      JOIN macrostrat.intervals ti ON ti.id = t_interval
      JOIN macrostrat.intervals tb ON tb.id = b_interval
     )
     -- Assign a color for making tiles
     SELECT map_id,
      unit_ids,
      strat_name_ids,
      lith_ids,

      best_age_top,
      best_age_bottom,

      (SELECT interval_color
       FROM macrostrat.intervals
       WHERE age_top <= best_age_top AND age_bottom >= best_age_bottom
       ORDER BY age_bottom - age_top
       LIMIT 1
      ) AS color
      FROM best_times


    )
    """, {"scale": AsIs(scale), "source_id": source_id})
    conn.commit()

def refresh_scale(scale):
    print "--- Working on ", scale, " ---"
    source_ids = find_sources(scale)
    for idx, source in enumerate(source_ids):
        print "--- ", idx, " of ", len(source_ids), " ---"
        refresh(scale, source)

if len(arguments.refresh) == 1:
    # Refresh all scales
    if arguments.refresh[0] == "all":
        for scale in valid_scales:
            refresh_scale(scale)
    else :
        scale = find_scale(arguments.refresh[0])
        if scale is not None:
            refresh(scale, arguments.refresh[0])
        elif arguments.refresh[0] in valid_scales:
            refresh_scale(arguments.refresh[0])
        else:
            print "Invalid source_id given"
