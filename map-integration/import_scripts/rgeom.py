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

    # Clean up
    call(['rm %s.*' % (primary_table ,)], shell=True)
    call(['rm %s_rgeom.*' % (primary_table, )], shell=True)

    # Write it to a shapefile
    call(['pgsql2shp -f %s.shp -u %s -h %s -p %s burwell sources.%s' % (primary_table, credentials.pg_user, credentials.pg_host, credentials.pg_port, primary_table)], shell=True)

    # Simplify it with mapshaper
    call(['mapshaper -i %s.shp -dissolve -o %s_rgeom.shp' % (primary_table, primary_table)], shell=True)

    # Import the simplified geometry into PostGIS
    call(['shp2pgsql -s 4326 -I %s_rgeom.shp public.%s_rgeom | psql -h %s -p %s -U %s -d burwell' % (primary_table, primary_table, credentials.pg_host, credentials.pg_port, credentials.pg_user)], shell=True)

    print 'Validating geometry...'
    cursor.execute("""
        ALTER TABLE public.%(primary_table)s ALTER COLUMN geom SET DATA TYPE geometry;

        UPDATE public.%(primary_table)s
        SET geom = ST_Buffer(geom, 0);
    """, {
        "primary_table": AsIs(primary_table + '_rgeom')
    })
    connection.commit()

    print 'Processing geometry...'
    # Update the sources table
    cursor.execute("""
        UPDATE maps.sources
        SET rgeom = (
            WITH dump AS (
              SELECT (ST_Dump(geom)).geom
              FROM public.%(primary_table)s
            ),
            types AS (
              SELECT ST_GeometryType(geom), geom
              FROM dump
              WHERE ST_GeometryType(geom) = 'ST_Polygon'
            ),
            rings AS (
              SELECT (ST_DumpRings(geom)).geom
              FROM types
            ),
            rings_numbered AS (
              SELECT a.geom, row_number() OVER () AS row_no
              FROM rings a
            ),
            containers AS (
              SELECT ST_Union(a.geom) AS GEOM, b.row_no
              FROM rings_numbered a JOIN rings_numbered b
              ON ST_Intersects(a.geom, b.geom)
              WHERE a.row_no != b.row_no
              GROUP BY b.row_no
            ),
            best AS (
              SELECT ST_Buffer(ST_Union(rings_numbered.geom), 0.0000001) geom
              FROM rings_numbered JOIN containers
              ON containers.row_no = rings_numbered.row_no
              WHERE NOT ST_Covers(containers.geom, rings_numbered.geom)
            )
            SELECT * FROM (
            SELECT 'best' as type, geom
            FROM best
            UNION
            SELECT 'next best' as type, geom
            FROM rings_numbered
            ) foo
            WHERE type = (
              CASE
                WHEN (SELECT count(*) FROM best) != NULL
                  THEN 'best'
                ELSE 'next best'
                END
            )
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
