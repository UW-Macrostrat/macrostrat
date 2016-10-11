import sys, os, time
from subprocess import call
import argparse
import psycopg2
from psycopg2.extensions import AsIs

sys.path = [os.path.join(os.path.dirname(__file__), os.pardir)] + sys.path
import credentials

parser = argparse.ArgumentParser(
    description="Create a carto table for a given scale",
    epilog="Example usage: python union.py 1")

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
        DROP TABLE IF EXISTS carto.%(scale)s
    """ % {
        "scale": arguments.the_scale
    })
    connection.commit()

    sql = []

    for scale_idx, scale in enumerate(layerOrder[arguments.the_scale]):
        # Skip if it is the target scale
        if scale == arguments.the_scale:
            sql.append("""
                SELECT map_id, '%(scale)s' AS scale, geom
                FROM carto.flat_%(scale)s
            """ % {"scale": scale})
            continue

        # Get the scales that are 'above' in the layer stacking order
        scales_above = ["'" + s + "'" for idx, s in enumerate(layerOrder[arguments.the_scale]) if idx > scale_idx]

        # Export reference geom
        call(['pgsql2shp -f rgeoms.shp -u %s -h %s -p %s burwell "SELECT 1 AS id, rgeom AS geom FROM maps.sources WHERE scale IN (%s)"' % (credentials.pg_user, credentials.pg_host, credentials.pg_port, ','.join(scales_above))], shell=True)

        # Union it
        call(['mapshaper -i rgeoms.shp -dissolve -o %s_rgeom.shp' % (scale, )], shell=True)

        # Import it
        call(['shp2pgsql -I -s 4326 %s_rgeom.shp public.%s_rgeom | psql -h %s -p %s -U %s -d burwell' % (scale, scale, credentials.pg_host, credentials.pg_port, credentials.pg_user)], shell=True)

        # Export intersecting geom
        call(['pgsql2shp -f intersecting.shp -u %s -h %s -p %s burwell "SELECT t.map_id, t.geom FROM carto.flat_%s t JOIN public.%s_rgeom sr ON ST_Intersects(t.geom, sr.geom)"' % (credentials.pg_user, credentials.pg_host, credentials.pg_port, scale, scale)], shell=True )

        # Remove the parts of the intersecting geoms that intersect scales above
        call(['mapshaper intersecting.shp -erase rgeom.shp -o clipped.shp'], shell=True)

        # Import the result to PostGIS
        call(['shp2pgsql -I -s 4326 clipped.shp public.%s_clipped | psql -h %s -p %s -U %s -d burwell' % (scale, credentials.pg_host, credentials.pg_port, credentials.pg_user)], shell=True)

        # Clean up shapefiles
        call(['rm intersecting.* && rm rgeom.* && rm clipped.* && rm _rgeom.* && rm rgeoms.*'], shell=True)

        # Build the SQL query
        sql.append("""
        SELECT t.map_id, '%(scale)s' AS scale, t.geom
        FROM carto.flat_%(scale)s t
        LEFT JOIN public.%(scale)s_rgeom sr
        ON ST_Intersects(t.geom, sr.geom)
        WHERE sr.gid IS NULL
        AND ST_Geometrytype(t.geom) != 'ST_LineString'

        UNION

        SELECT map_id, '%(scale)s' AS scale, geom
        FROM %(scale)s_clipped
        """ % {'scale': scale, 'scales_above': ','.join(scales_above)})


    m_join = ' UNION '.join(['SELECT map_id, source_id, name, strat_name, age, lith, descrip, comments, t_interval, b_interval FROM maps.%s' % scale for scale in layerOrder[arguments.the_scale]])

    l_join = ' UNION '.join(['SELECT map_id, best_age_top, best_age_bottom, color FROM public.lookup_%s' % scale for scale in layerOrder[arguments.the_scale]])


    to_run = """
        CREATE TABLE carto.%(scale)s AS
        SELECT r.map_id, r.scale, m.source_id,
        COALESCE(m.name, '') AS name,
        COALESCE(m.strat_name, '') AS strat_name,
        COALESCE(m.age, '') AS age,
        COALESCE(m.lith, '') AS lith,
        COALESCE(m.descrip, '') AS descrip,
        COALESCE(m.comments, '') AS comments,
        cast(l.best_age_top as numeric) AS best_age_top,
        cast(l.best_age_bottom as numeric) AS best_age_bottom, it.interval_name t_int, ib.interval_name b_int, l.color,
        ST_SetSRID(r.geom, 4326) AS geom
        FROM (
            %(sql)s
        ) r
        LEFT JOIN (
            %(m_join)s
        ) m ON r.map_id = m.map_id
        LEFT JOIN (
            %(l_join)s
        ) l ON r.map_id = l.map_id
        JOIN macrostrat.intervals it ON m.t_interval = it.id
        JOIN macrostrat.intervals ib ON m.b_interval = ib.id
        WHERE ST_NumGeometries(r.geom) > 0;

        CREATE INDEX ON carto.%(scale)s (map_id);
        CREATE INDEX ON carto.%(scale)s USING GiST (geom);
    """ % {
        'scale': scale,
        'sql': ' UNION '.join(sql),
        'm_join': m_join,
        'l_join': l_join
    }

    cursor.execute(to_run)
    connection.commit()

    drop = ''

    for scale in layerOrder[arguments.the_scale]:
        drop += 'DROP TABLE IF EXISTS %s_clipped; DROP TABLE IF EXISTS %s_rgeom;' % (scale, scale,)

    cursor.execute(drop)
    connection.commit()

    end = time.time()
    print 'Created carto.%s in ' % scale, int(end - start), 's'
