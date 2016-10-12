import sys, os, time
from subprocess import call
import argparse
import psycopg2
from psycopg2.extensions import AsIs

sys.path = [os.path.join(os.path.dirname(__file__), os.pardir)] + sys.path
import credentials

parser = argparse.ArgumentParser(
    description="Create a carto table for a given scale",
    epilog="Example usage: python carto_lines.py small")

parser.add_argument(nargs="?", dest="the_scale",
    default="0", type=str,
    help="The scale to generate a carto table for")

arguments = parser.parse_args()

# For a given scale, define which scales go into the carto table (ordered from 'bottom' to 'top' if you think of them as stacked)
layerOrder = {
    "tiny": ["tiny"],
    "small": ["tiny", "small"],
    "medium": ["small", "medium"],
    "large": ["medium", "large"]
}

if arguments.the_scale not in layerOrder:
    print 'Please enter a valid scale', [scale for scale in layerOrder]
    sys.exit(1)

if __name__ == '__main__':
    start = time.time()
    connection = psycopg2.connect(dbname="burwell", user=credentials.pg_user, host=credentials.pg_host, port=credentials.pg_port)
    cursor = connection.cursor()

    # Clean up
    cursor.execute("""
        DROP TABLE IF EXISTS carto_lines.%(scale)s
    """ % {
        "scale": arguments.the_scale
    })
    connection.commit()

    sql = []

    for scale_idx, scale in enumerate(layerOrder[arguments.the_scale]):
        # Skip if it is the target scale
        if scale == arguments.the_scale:
            sql.append("""
                SELECT line_id, '%(scale)s' AS scale, geom
                FROM carto_lines.flat_%(scale)s
            """ % {"scale": scale})
            continue

        # Get the scales that are 'above' in the layer stacking order
        scales_above = ["'" + s + "'" for idx, s in enumerate(layerOrder[arguments.the_scale]) if idx > scale_idx]

        # Export reference geom
        call(['pgsql2shp -f rgeom.shp -u %s -h %s -p %s burwell "SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom FROM maps.sources WHERE scale IN (%s)"' % (credentials.pg_user, credentials.pg_host, credentials.pg_port, ','.join(scales_above))], shell=True)

        # Export intersecting geom
        call(['pgsql2shp -f intersecting.shp -u %s -h %s -p %s burwell "SELECT t.line_id, t.geom FROM carto_lines.flat_%s t JOIN ( SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom FROM maps.sources WHERE scale IN (%s) ) sr ON ST_Intersects(t.geom, sr.geom)"' % ( credentials.pg_user, credentials.pg_host, credentials.pg_port, scale, ','.join(scales_above))], shell=True)

        # Remove the parts of the intersecting geoms that intersect scales above
        call(['mapshaper intersecting.shp -erase rgeom.shp -o clipped.shp'], shell=True)

        # Import the result to PostGIS
        call(['shp2pgsql -s 4326 clipped.shp public.%s_clipped | psql -h %s -p %s -U %s -d burwell' % (scale, credentials.pg_host, credentials.pg_port, credentials.pg_user)], shell=True)

        # Clean up shapefiles
        call(['rm intersecting.* && rm rgeom.* && rm clipped.*'], shell=True)

        # Build the SQL query
        sql.append("""
        SELECT t.line_id, '%(scale)s' AS scale, t.geom
        FROM carto_lines.flat_%(scale)s t
        LEFT JOIN (
          SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom
          FROM maps.sources
          WHERE scale IN (%(scales_above)s)
        ) sr
        ON ST_Intersects(t.geom, sr.geom)
        WHERE sr.id IS NULL
        AND ST_Geometrytype(t.geom) != 'ST_LineString'

        UNION

        SELECT line_id, '%(scale)s' AS scale, geom
        FROM %(scale)s_clipped
        """ % {'scale': scale, 'scales_above': ','.join(scales_above)})


    m_join = ' UNION '.join(['SELECT line_id, source_id, name, type, direction, descrip FROM lines.%s' % scale for scale in layerOrder[arguments.the_scale]])


    to_run = """
        CREATE TABLE carto_lines.%(scale)s AS
        SELECT r.line_id, r.scale, m.source_id,
        COALESCE(m.name, '') AS name,
        COALESCE(m.type, '') AS type,
        COALESCE(m.direction, '') AS direction,
        COALESCE(m.descrip, '') AS descrip,
        ST_SetSRID(r.geom, 4326) AS geom
        FROM (
            %(sql)s
        ) r
        LEFT JOIN (
            %(m_join)s
        ) m ON r.line_id = m.line_id
        WHERE ST_NumGeometries(r.geom) > 0;

        CREATE INDEX ON carto_lines.%(scale)s (line_id);
        CREATE INDEX ON carto_lines.%(scale)s USING GiST (geom);
    """ % {
        'scale': scale,
        'sql': ' UNION '.join(sql),
        'm_join': m_join
    }

    cursor.execute(to_run)
    connection.commit()

    drop = ''

    for scale in layerOrder[arguments.the_scale]:
        drop += 'DROP TABLE IF EXISTS %s_clipped;' % scale

    cursor.execute(drop)
    connection.commit()

    end = time.time()
    print 'Created carto_lines.%s in ' % scale, int(end - start), 's'
