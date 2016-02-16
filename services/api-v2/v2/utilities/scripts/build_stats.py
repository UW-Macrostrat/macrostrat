import MySQLdb
import MySQLdb.cursors
import psycopg2
from warnings import filterwarnings
import sys
from credentials import *

# Connect to Macrostrat
try:
  connection = MySQLdb.connect(host=mysql_host, user=mysql_user, passwd=mysql_passwd, db=mysql_db, unix_socket=mysql_unix_socket, cursorclass=MySQLdb.cursors.DictCursor)
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

# Cursor for MySQL
cursor = connection.cursor()

# Ignore warnings
filterwarnings('ignore', category = MySQLdb.Warning)

# Connect to Postgres
pg_conn = psycopg2.connect(dbname=pg_db, user=pg_user, host=pg_host, port=pg_port)
pg_cur = pg_conn.cursor()


cursor.execute("""
    DROP TABLE IF EXISTS stats
""")
cursor.close()

cursor = connection.cursor()
cursor.execute("""
    CREATE TABLE stats AS (
        SELECT
          projects.id AS project_id,
          projects.project,
          unit_counts.columns,
          unit_counts.packages,
          unit_counts.units,
          collection_counts.pbdb_collections,
          measure_counts.measurements
        FROM projects
        JOIN (
          SELECT project_id, count(distinct col_id) AS columns, count(distinct section_id) AS packages, count(distinct unit_id) AS units
          FROM (
            SELECT DISTINCT project_id, units_sections.section_id, units_sections.col_id, units_sections.unit_id
            FROM units_sections
            JOIN cols ON cols.id = units_sections.col_id
            WHERE cols.status_code = 'active'
          ) distinct_units
          GROUP BY distinct_units.project_id
        ) AS unit_counts ON unit_counts.project_id = projects.id
        JOIN (
          SELECT project_id, count(distinct id) AS measurements
          FROM (
            SELECT DISTINCT project_id, measures.id
            FROM cols
            JOIN units_sections ON cols.id = units_sections.col_id
            LEFT JOIN unit_measures ON unit_measures.unit_id = units_sections.unit_id
            LEFT JOIN measures ON unit_measures.measuremeta_id = measures.measuremeta_id
            WHERE cols.status_code = 'active'
          ) AS distinct_measures
          GROUP BY distinct_measures.project_id
        ) AS measure_counts ON measure_counts.project_id = projects.id
        JOIN (
          SELECT project_id, count(distinct collection_no) AS pbdb_collections
          FROM (
            SELECT DISTINCT project_id, collection_no
            FROM cols
            JOIN units_sections ON units_sections.col_id = cols.id
            LEFT JOIN pbdb_matches ON pbdb_matches.unit_id = units_sections.unit_id
            WHERE cols.status_code = 'active'
          ) AS distinct_collections
          GROUP BY distinct_collections.project_id
        ) AS collection_counts ON collection_counts.project_id = projects.id
        WHERE project IN ('North America','New Zealand','Caribbean','Deep Sea')
    )
""")

cursor.execute("""
    ALTER TABLE stats ADD COLUMN burwell_polygons integer default 0;
""")

cursor.close()
cursor = connection.cursor()

pg_cur.execute("""
    select count(*)
    FROM (SELECT map_id FROM maps.tiny
    UNION SELECT map_id FROM maps.small
    UNION SELECT map_id FROM maps.medium
    UNION SELECT map_id FROM maps.large) foo
""")
count = pg_cur.fetchone()[0]

print count
cursor.execute("UPDATE stats SET burwell_polygons = %d" % count)
connection.commit()

cursor.close()

print "Done updating stats"
