import argparse
import time
import psycopg2
from psycopg2.extensions import AsIs
import sys
import os

sys.path = [os.path.join(os.path.dirname(__file__), os.pardir)] + sys.path
import credentials

connection = psycopg2.connect(dbname="burwell", user=credentials.pg_user, host=credentials.pg_host, port=credentials.pg_port)
cursor = connection.cursor()


parser = argparse.ArgumentParser(
  description="Match rocks to Macrostrat units",
  epilog="Example usage: python match.py --source_id 2 --table medium")

parser.add_argument("-s", "--source_id", dest="source_id",
  default="0", type=str, required=True,
  help="The ID of the desired source to match")

parser.add_argument("-t", "--table", dest="table",
  default="small", type=str, required=True,
  help="The scale table to use. Can be 'small', 'medium', or 'large'.")

arguments = parser.parse_args()

# Validate params!
if arguments.table not in ["small", "medium", "large"]:
    print "Invalid table argument"
    sys.exit(1)

cursor.execute("SELECT source_id FROM maps.sources")
sources = cursor.fetchall()
source_ids = [source[0] for source in sources]
if int(arguments.source_id) not in source_ids:
    print "Invalid source_id argument. Source ID ", arguments.source_id, " was not found in maps.sources"
    sys.exit(1)

# Clean up
cursor.execute("""
    DELETE FROM maps.map_units WHERE map_id IN (SELECT map_id FROM maps.%(table)s WHERE source_id = %(source_id)s)
""", {
    "table": AsIs(arguments.table),
    "source_id": AsIs(arguments.source_id)
})

cursor.execute("""
    DELETE FROM maps.map_strat_names WHERE map_id IN (SELECT map_id FROM maps.%(table)s WHERE source_id = %(source_id)s)
""", {
    "table": AsIs(arguments.table),
    "source_id": AsIs(arguments.source_id)
})
connection.commit()
print "------- Done cleaning up -------"


# Time the process
start_time = time.time()

print "------- Starting query... -------"
# Do it
cursor.execute("""
WITH rocks AS (SELECT map_id, strat_name, name, descrip, comments, intervals_top.age_top, intervals_bottom.age_bottom, 25 as age_buffer, geom
          FROM maps.%(table)s
          JOIN macrostrat.intervals intervals_top on t_interval = intervals_top.id
          JOIN macrostrat.intervals intervals_bottom on b_interval = intervals_bottom.id
          WHERE source_id = %(source_id)s
 ),
 macro AS (
  WITH first AS (
    SELECT DISTINCT lsn.strat_name_id,
      unnest(array(
        SELECT not_null_names FROM (
          SELECT unnest(
            array[lsn.bed_name, lsn.mbr_name, lsn.fm_name, lsn.gp_name, lsn.sgp_name]
          ) not_null_names
        ) sub WHERE not_null_names IS NOT NULL
      )) AS names,

      unnest(array(
        SELECT not_null_ids FROM (
          SELECT unnest(
            array[lsn.bed_id, lsn.mbr_id, lsn.fm_id, lsn.gp_id, lsn.sgp_id]
          ) not_null_ids
        ) sub WHERE not_null_ids != 0
      )) AS strat_name_ids
    FROM macrostrat.lookup_strat_names lsn
    JOIN macrostrat.unit_strat_names usn ON usn.strat_name_id = lsn.strat_name_id
    ORDER BY lsn.strat_name_id
  )

  SELECT units.id AS unit_id, first.names AS strat_name, first.strat_name_ids AS strat_name_id, lui.lo_age AS age_top, lui.fo_age AS age_bottom, poly_geom
  FROM macrostrat.units
  JOIN macrostrat.unit_strat_names usn ON units.id = usn.unit_id
  JOIN first ON first.strat_name_id = usn.strat_name_id
  JOIN macrostrat.cols ON cols.id = units.col_id
  JOIN macrostrat.lookup_unit_intervals lui ON units.id = lui.unit_id
  WHERE cols.status_code = 'active'
 )
SELECT DISTINCT rocks.map_id, macro.unit_id, macro.strat_name_id FROM rocks, macro
WHERE macro.strat_name != '' AND ST_Intersects(rocks.geom, macro.poly_geom) AND (

	rocks.strat_name ~* concat('\y', macro.strat_name, '\y') OR
    rocks.name ~* concat('\y', macro.strat_name, '\y') OR
    rocks.descrip ~* concat('\y', macro.strat_name, '\y') OR
    rocks.comments ~* concat('\y', macro.strat_name, '\y')

) AND (((macro.age_top) <= (rocks.age_bottom + rocks.age_buffer))
AND ((rocks.age_top - rocks.age_buffer) <= (macro.age_bottom)))
""", {
  "table": AsIs(arguments.table),
  "source_id": AsIs(arguments.source_id)
})

results = cursor.fetchall()
print "------- Got results....inserting -------"
for row in results:
    # 0 = map_id, 1 = unit_id, 2 = strat_name_id
    # Insert into maps.map_units
    cursor.execute("""
        INSERT INTO maps.map_units VALUES (%(map_id)s, %(unit_id)s)
    """, {
        "map_id": row[0],
        "unit_id": row[1]
    })

    # Insert into maps.map_strat_names
    cursor.execute("""
        INSERT INTO maps.map_strat_names VALUES (%(map_id)s, %(strat_name_id)s)
    """, {
        "map_id": row[0],
        "strat_name_id": row[2]
    })

connection.commit()

elapsed = int(time.time() - start_time)
print "Inserted ", len(results), " into maps.unit_strat_names and maps.units in ", elapsed / 60, " minutes and ", elapsed % 60, " seconds"
