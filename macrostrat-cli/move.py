import MySQLdb
import MySQLdb.cursors
import os
import psycopg2
from psycopg2.extensions import AsIs
import sys
import subprocess
import yaml
import datetime
from table_meta import *

with open(os.path.join(os.path.dirname(__file__), './credentials.yml'), 'r') as f:
    credentials = yaml.load(f)

# Connect to Postgres
pg_conn = psycopg2.connect(dbname=credentials['pg_db'], user=credentials['pg_user'], host=credentials['pg_host'], port=credentials['pg_port'])
pg_conn.set_client_encoding('Latin1')
pg_cur = pg_conn.cursor()

# Connect to MySQL
my_conn = MySQLdb.connect(host=credentials['mysql_host'], user=credentials['mysql_user'], passwd=credentials['mysql_passwd'], db=credentials['mysql_db'], unix_socket=credentials['mysql_socket'], cursorclass=MySQLdb.cursors.SSCursor)
my_cur = my_conn.cursor()

def move_table(table):
    print '     %s' % (table, )
    # Clean up
    pg_cur.execute("DROP TABLE IF EXISTS macrostrat.%(table)s_new", { "table": AsIs(table) })
    pg_conn.commit()

    # Create the new table in Postgres
    pg_cur.execute(tables[table]["create"])
    pg_conn.commit()

    # Dump the data from MariaDB
    my_cur.execute(tables[table]["dump"])

    # Iterate on each row and insert into Postgres
    row = my_cur.fetchone()
    while row is not None:
        pg_cur.execute(tables[table]["insert"], row)
        row = my_cur.fetchone()
    pg_conn.commit()

    # Add any indexes
    pg_cur.execute(tables[table]["index"])
    pg_conn.commit()

    # Run processing steps, if needed
    if len(tables[table]["process"].strip()) != 0:
        pg_cur.execute(tables[table]["process"])
        pg_conn.commit()

    # Rename the table, drop the old one, add updated comment
    pg_cur.execute("""
        COMMENT ON TABLE macrostrat.%(table)s_new IS %(time)s;
        ALTER TABLE macrostrat.%(table)s RENAME TO %(table)s_old;
        ALTER TABLE macrostrat.%(table)s_new RENAME TO %(table)s;
        DROP TABLE macrostrat.%(table)s_old;
    """, { "table": AsIs(table), "time": 'Last updated from MariaDB - ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M') })
    pg_conn.commit()

if len(sys.argv) == 1:
    print 'Please specify a table to move from MariaDB to Postgres'
    for table in tables:
        print '   %s' % (table, )
    sys.exit()

# Validate the passed table
table = sys.argv[1]
if table not in tables and table != 'all':
    print 'Invalid table'
    sys.exit()

if table == 'all':
    for t in tables:
        move_table(t)
else:
    move_table(table)
