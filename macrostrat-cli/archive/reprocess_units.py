import sys
import pymysql
import pymysql.cursors
from warnings import filterwarnings
import os
import psycopg2
from psycopg2.extensions import AsIs
import yaml
import datetime

# Load the credentials file
with open(os.path.join(os.path.dirname(__file__), './credentials.yml'), 'r') as f:
    credentials = yaml.load(f)

# Connect to MySQL
def mariaConnection():
    # Ignore warnings from MariaDB
    filterwarnings('ignore', category = pymysql.Warning)
    return pymysql.connect(host=credentials['mysql_host'], user=credentials['mysql_user'], passwd=credentials['mysql_passwd'], db=credentials['mysql_db'], unix_socket=credentials['mysql_socket'], cursorclass=pymysql.cursors.SSDictCursor, read_timeout=180)

# Connect to Postgres
def pgConnection():
    pg_conn = psycopg2.connect(dbname=credentials['pg_db'], user=credentials['pg_user'], host=credentials['pg_host'], port=credentials['pg_port'])
    pg_conn.set_client_encoding('Latin1')
    return pg_conn


from cli.commands.match_scripts import units
from cli.commands.process_scripts import burwell_lookup
unit_processing = units({
    'pg': pgConnection,
    'mariadb': mariaConnection,
    'credentials': credentials
})
lookup_processing = burwell_lookup({
    'pg': pgConnection,
    'mariadb': mariaConnection,
    'credentials': credentials
})


pg_connection = pgConnection()
pg_cursor = pg_connection.cursor()

pg_cursor.execute("""
    SELECT source_id
    FROM maps.sources
    WHERE scale = 'small'
    ORDER BY source_id
""")
sources = pg_cursor.fetchall()

pg_connection.close()

for source in sources:
    print 'WORKING ON %s' % (source[0], )
    unit_processing.run(source[0])
    lookup_processing.run(source[0])

