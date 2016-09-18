import sys, os, time
from subprocess import call
import argparse
import psycopg2
from psycopg2.extensions import AsIs

sys.path = [os.path.join(os.path.dirname(__file__), os.pardir)] + sys.path
import credentials

parser = argparse.ArgumentParser(
    description="Creat a unioned reference geometry for a given source",
    epilog="Example usage: python union.py 1")

parser.add_argument(nargs="?", dest="source_id",
    default="0", type=int,
    help="The ID of the desired source to union")

arguments = parser.parse_args()

if arguments.source_id == 0:
    sys.exit(1)

if __name__ == '__main__':
    start = time.time()
    connection = psycopg2.connect(dbname="burwell", user=credentials.pg_user, host=credentials.pg_host, port=credentials.pg_port)
    cursor = connection.cursor()

    # Get the primary table of the target source
    cursor.execute("""
        SELECT primary_table
        FROM maps.sources
        WHERE source_id = %(source_id)s
    """, {
        "source_id": arguments.source_id
    })

    result = cursor.fetchone()

    primary_table = result[0]

    # Write it to a shapefile
    call(['pgsql2shp -f %s.shp -u %s -h %s -p %s burwell sources.%s' % (primary_table, credentials.pg_user, credentials.pg_host, credentials.pg_port, primary_table)], shell=True)

    # Simplify it with mapshaper
    call(['mapshaper -i %s.shp -dissolve -o %s_rgeom.shp' % (primary_table, primary_table)], shell=True)

    # Import the simplified geometry into PostGIS
    call(['shp2pgsql -s 4326 -I %s_rgeom.shp public.%s_rgeom | psql -h %s -p %s -U %s -d burwell' % (primary_table, primary_table, credentials.pg_host, credentials.pg_port, credentials.pg_user)], shell=True)

    # Update the sources table
    cursor.execute("""
        UPDATE maps.sources
        SET rgeom = (
            SELECT ST_MakeValid(geom)
            FROM public.%(primary_table)s
        )
        WHERE source_id = %(source_id)s
    """, {
        "primary_table": AsIs(primary_table + '_rgeom'),
        "source_id": arguments.source_id
    })
    connection.commit()
    print 'Done inserting new geometry'

    # Drop the temporary table
    cursor.execute("""
        DROP TABLE public.%(primary_table)s
    """, {
        "primary_table": AsIs(primary_table + '_rgeom')
    })
    connection.commit()
    print 'Done dropping temp table'

    # Clean up the working directory
    call(['rm %s*' % (primary_table, )], shell=True)

    end = time.time()

    print 'Done in ', int(end - start), 's'
