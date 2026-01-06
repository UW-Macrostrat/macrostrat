import argparse
import os
import sys
import time
from subprocess import call

import psycopg2
import yaml
from psycopg2.extensions import AsIs

with open('../credentials.yml', 'r') as f:
    credentials = yaml.load(f)

parser = argparse.ArgumentParser(
    description="Create a carto table for a given source or scale",
    epilog="Example usage: python carto.py -s 123 --or-- python carto.py small")

parser.add_argument("-s", "--source_id", dest="source_id",
  default="", type=str, required=True,
  help="The source_id that should be added to the carto tables")

arguments = parser.parse_args()

'''
@source_id - the source to schlep
1. Validate source_id
2. Find primary geology, lines, and points tables
3. Dump from:
    a. maps.sources
    b. maps.map_units
    c. maps.map_liths
    d. maps.map_strat_names
    g. lookup_<scale>
    h. maps.<scale>
'''


if __name__ == '__main__':
    if not arguments.source_id:
        sys.exit(1)

    start = time.time()
    connection = psycopg2.connect(dbname=credentials["pg_db"], user=credentials["pg_user"], host=credentials["pg_host"], port=credentials["pg_port"])
    cursor = connection.cursor()

    cursor.execute("SELECT scale, primary_table, primary_line_table FROM maps.sources WHERE source_id = %(source_id)s", { "source_id": arguments.source_id })
    scale, primary_table, primary_lines_table = cursor.fetchone()

    if not scale:
        print 'Invalid source_id'
        sys.exit()

    # maps.sources
    call(['psql -U %s -p %s -h %s burwell -c "COPY (SELECT * FROM maps.sources WHERE source_id = %s) TO stdout" | psql -U %s -p %s -h %s burwell -c "COPY maps.sources FROM stdin"' % (credentials['pg_user'], credentials['pg_port'], credentials['pg_host'], arguments.source_id, credentials['pg_user_remote'], credentials['pg_port_remote'], credentials['pg_host_remote'])], shell=True)

    # maps.map_liths
    call(['psql -U %s -p %s -h %s burwell -c "COPY (SELECT * FROM maps.map_liths WHERE map_id IN (SELECT map_id FROM maps.%s WHERE source_id = %s)) TO stdout" | psql -U %s -p %s -h %s burwell -c "COPY maps.map_liths FROM stdin"' % (credentials['pg_user'], credentials['pg_port'], credentials['pg_host'], scale, arguments.source_id, credentials['pg_user_remote'], credentials['pg_port_remote'], credentials['pg_host_remote'])], shell=True)

    # maps.map_units
    call(['psql -U %s -p %s -h %s burwell -c "COPY (SELECT * FROM maps.map_units WHERE map_id IN (SELECT map_id FROM maps.%s WHERE source_id = %s)) TO stdout" | psql -U %s -p %s -h %s burwell -c "COPY maps.map_units FROM stdin"' % (credentials['pg_user'], credentials['pg_port'], credentials['pg_host'], scale, arguments.source_id, credentials['pg_user_remote'], credentials['pg_port_remote'], credentials['pg_host_remote'])], shell=True)

    # maps.map_strat_names
    call(['psql -U %s -p %s -h %s burwell -c "COPY (SELECT * FROM maps.map_strat_names WHERE map_id IN (SELECT map_id FROM maps.%s WHERE source_id = %s)) TO stdout" | psql -U %s -p %s -h %s burwell -c "COPY maps.map_strat_names FROM stdin"' % (credentials['pg_user'], credentials['pg_port'], credentials['pg_host'], scale, arguments.source_id, credentials['pg_user_remote'], credentials['pg_port_remote'], credentials['pg_host_remote'])], shell=True)

    # lookup_<scale>
    call(['psql -U %s -p %s -h %s burwell -c "COPY (SELECT l.* FROM public.lookup_%s l JOIN maps.%s m ON m.map_id = l.map_id  WHERE source_id = %s) TO stdout" | psql -U %s -p %s -h %s burwell -c "COPY public.lookup_%s FROM stdin"' % (credentials['pg_user'], credentials['pg_port'], credentials['pg_host'], scale, scale, arguments.source_id, credentials['pg_user_remote'], credentials['pg_port_remote'], credentials['pg_host_remote'], scale)], shell=True)

    # maps.<scale>
    call(['psql -U %s -p %s -h %s burwell -c "COPY (SELECT * FROM maps.%s WHERE source_id = %s) TO stdout" | psql -U %s -p %s -h %s burwell -c "COPY maps.%s FROM stdin"' % (credentials['pg_user'], credentials['pg_port'], credentials['pg_host'], scale, arguments.source_id, credentials['pg_user_remote'], credentials['pg_port_remote'], credentials['pg_host_remote'], scale)], shell=True)
