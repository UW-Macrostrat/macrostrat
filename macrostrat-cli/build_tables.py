import pymysql
import pymysql.cursors
from warnings import filterwarnings
import os
import psycopg2
from psycopg2.extensions import AsIs
import sys
import subprocess
import yaml
import datetime
import build

# Load the credentials file
with open(os.path.join(os.path.dirname(__file__), './credentials.yml'), 'r') as f:
    credentials = yaml.load(f)

# Connect to MySQL
def mariaConnection():
    return pymysql.connect(host=credentials['mysql_host'], user=credentials['mysql_user'], passwd=credentials['mysql_passwd'], db=credentials['mysql_db'], unix_socket=credentials['mysql_socket'], cursorclass=pymysql.cursors.SSDictCursor, read_timeout=180)

# Connect to Postgres
def pgConnection():
    pg_conn = psycopg2.connect(dbname=credentials['pg_db'], user=credentials['pg_user'], host=credentials['pg_host'], port=credentials['pg_port'])
    pg_conn.set_client_encoding('Latin1')
    return pg_conn

# Ignore warnings from MariaDB
filterwarnings('ignore', category = pymysql.Warning)

# Check if a table was provided
if len(sys.argv) == 1:
    print 'Please specify a table'
    for table in dir(build):
        if table[:2] != '__':
            print '   %s' % (table, )
    sys.exit()

# Validate the passed table
table = sys.argv[1]
if table not in dir(build):
    print 'Invalid table'
    sys.exit()

# Get the class associated with the provided table name
script = getattr(build, table)

print '    Building %s' % (table, )

if script.meta['mariadb'] and script.meta['pg']:
    script.build(mariaConnection, pgConnection)
elif script.meta['mariadb']:
    script.build(mariaConnection)
elif script.meta['pg']:
    script.build(pgConnection)
else:
    print 'Build script does not specify connector type'
    sys.exit()

print '    Done building %s' % (table, )
