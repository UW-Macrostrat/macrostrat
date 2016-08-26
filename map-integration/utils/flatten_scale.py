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

parser.add_argument(nargs="?", dest="scale",
    default="0", type=str,
    help="The scale to union")

arguments = parser.parse_args()

if arguments.scale == "0":
    sys.exit(1)

if __name__ == '__main__':
    start = time.time()
    connection = psycopg2.connect(dbname="burwell", user=credentials.pg_user, host=credentials.pg_host, port=credentials.pg_port)
    cursor = connection.cursor()

    scale = arguments.scale

    # First check if there is anything high priority in this scale
    cursor.execute("""
        SELECT source_id
        FROM maps.sources
        WHERE scale = %(scale)s
            AND priority IS TRUE
    """, {
        "scale": scale
    })
    results = cursor.fetchall()

    if len(results) > 0:
        # High priority mask (use as clipping mask)
        call(['pgsql2shp -f high_priority_mask.shp -u %s -h %s -p %s burwell "SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom FROM maps.sources WHERE scale = \'%s\' AND priority IS TRUE"' % (credentials.pg_user, credentials.pg_host, credentials.pg_port, scale)], shell=True)

        # low priority intersections
        call(['pgsql2shp -f low_priority_intersections.shp -u %s -h %s -p %s burwell "SELECT s.map_id, s.geom FROM maps.%s s JOIN maps.sources ON s.source_id = sources.source_id JOIN ( SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom FROM maps.sources WHERE scale = \'%s\' AND priority IS TRUE) pr ON ST_Intersects(s.geom, st_setsrid(pr.geom, 4326)) WHERE priority IS FALSE AND ST_NumGeometries(s.geom) > 0"' % (credentials.pg_user, credentials.pg_host, credentials.pg_port, scale, scale)], shell=True)

        # Remove the parts of low priority intersects that overlap with the high priority areas
        call(['mapshaper low_priority_intersections.shp -erase high_priority_mask.shp -o low_priority_clipped.shp'], shell=True)

        # Combine the results into one shapefile
        #call(['mapshaper -i high_priority.shp low_priority.shp low_priority_clipped.shp combine-files -merge-layers -o small.shp'], shell=True)

        # Import the clipped geometry into PostGIS
        call(['shp2pgsql -s 4326 low_priority_clipped.shp public.low_priority_clipped | psql -h %s -p %s -U %s -d burwell' % (credentials.pg_host, credentials.pg_port, credentials.pg_user)], shell=True)

        # Recreate the flattened table
        cursor.execute("""
        DROP TABLE IF EXISTS carto.flat_%(scale)s;

        CREATE TABLE carto.flat_%(scale)s AS
            SELECT s.map_id, s.geom
            FROM maps.small s
            JOIN maps.sources ON s.source_id = sources.source_id
            WHERE priority IS TRUE
            AND ST_NumGeometries(s.geom) > 0

            UNION

            SELECT s.map_id, s.geom
            FROM maps.small s
            JOIN maps.sources ON s.source_id = sources.source_id
            LEFT JOIN (
              SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom
              FROM maps.sources
              WHERE scale = '%(scale)s'
              AND priority IS TRUE
            ) pr
            ON ST_Intersects(s.geom, st_setsrid(pr.geom, 4326))
            WHERE pr.id IS NULL
            AND priority IS FALSE
            AND ST_Geometrytype(s.geom) != 'ST_LineString'
            AND ST_NumGeometries(s.geom) > 0

            UNION

            SELECT map_id, geom
            FROM public.low_priority_clipped;

        CREATE INDEX ON carto.flat_%(scale)s (map_id);
        CREATE INDEX ON carto.flat_%(scale)s USING GiST (geom);
        """, {
            "scale": AsIs(scale)
        })
        connection.commit()

        # Drop the temporary table
        cursor.execute("""
            DROP TABLE public.low_priority_clipped
        """, {})
        connection.commit()

        # Clean up the working directory
        call(['rm high_priority*'], shell=True)
        call(['rm low_priority*'], shell=True)

    else:
        cursor.execute("""
        DROP TABLE IF EXISTS carto.flat_%(scale)s;

        CREATE TABLE carto.flat_%(scale)s AS
            SELECT s.map_id, s.geom
            FROM maps.small s
            WHERE ST_NumGeometries(s.geom) > 0;

        CREATE INDEX ON carto.flat_%(scale)s (map_id);
        CREATE INDEX ON carto.flat_%(scale)s USING GiST (geom);
        """, {
            "scale": AsIs(scale)
        })
        connection.commit()

    end = time.time()

    print 'Done in ', int(end - start), 's'
