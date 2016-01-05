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
      WITH first as (
        SELECT
          st.map_id,
          st.source_id,
          array(
            select distinct unit_id
            FROM maps.map_units m
            WHERE st.map_id = m.map_id
            AND basis_col =
              ANY(CASE
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
                WHEN 'descrip_buffer' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
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
            AND basis_col =
              ANY(CASE
                WHEN 'manual_replace' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
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
                WHEN 'descrip_buffer' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
                  array['descrip', 'manual']
                WHEN 'comments_buffer' IN (SELECT DISTINCT basis_col FROM maps.map_strat_names m WHERE st.map_id = m.map_id) THEN
                  array['comments_buffer', 'manual']
                ELSE
                 array['unknown', 'manual']
               END)
          ) AS strat_name_ids,

          array(
            SELECT DISTINCT lith_id
            FROM maps.map_liths m
            WHERE st.map_id = m.map_id
            AND basis_col =
              ANY(CASE
                WHEN 'manual_replace' IN (SELECT DISTINCT basis_col FROM maps.map_units m WHERE st.map_id = m.map_id) THEN
                  array['manual_replace']
                WHEN 'lith' IN (SELECT DISTINCT basis_col FROM maps.map_liths m WHERE st.map_id = m.map_id) THEN
                  array['lith', 'manual']
                WHEN 'descrip' IN (SELECT DISTINCT basis_col FROM maps.map_liths m WHERE st.map_id = m.map_id) THEN
                  array['descrip', 'manual']
                WHEN 'comments' IN (SELECT DISTINCT basis_col FROM maps.map_liths m WHERE st.map_id = m.map_id) THEN
                  array['comments', 'manual']
                WHEN 'name' IN (SELECT DISTINCT basis_col FROM maps.map_liths m WHERE st.map_id = m.map_id) THEN
                  array['name', 'manual']
                WHEN 'strat_name' IN (SELECT DISTINCT basis_col FROM maps.map_liths m WHERE st.map_id = m.map_id) THEN
                  array['strat_name', 'manual']
                ELSE
                  array['unknown', 'manual']
                END
              )
          ) AS lith_ids,

          t_interval,
          b_interval

        FROM maps.%(scale)s st
        LEFT JOIN maps.map_units mu ON mu.map_id = st.map_id
        LEFT JOIN maps.map_strat_names msn ON msn.map_id = st.map_id
        WHERE st.source_id = %(source_id)s
        GROUP BY st.map_id
        ),
        -- Get the min t_age and max b_age
        second AS (SELECT
          map_id,
          source_id,
          unit_ids,
          strat_name_ids,
          lith_ids,
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

         FROM second
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
         FROM third
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
