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
    "small": ["tiny", "large", "medium", "small"],
    "medium": ["large", "small", "medium"],
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
        call(['pgsql2shp -f rgeom.shp -u %s -h %s -p %s burwell "SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom FROM maps.sources WHERE scale IN (%s)"' % (credentials.pg_user, credentials.pg_host, credentials.pg_port, ','.join(scales_above))], shell=True)

        # Export intersecting geom
        call(['pgsql2shp -f intersecting.shp -u %s -h %s -p %s burwell "SELECT t.map_id, t.geom FROM carto.flat_%s t JOIN ( SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom FROM maps.sources WHERE scale IN (%s) ) sr ON ST_Intersects(t.geom, sr.geom)"' % ( credentials.pg_user, credentials.pg_host, credentials.pg_port, scale, ','.join(scales_above))], shell=True)

        # Remove the parts of the intersecting geoms that intersect scales above
        call(['mapshaper intersecting.shp -erase rgeom.shp -o clipped.shp'], shell=True)

        # Import the result to PostGIS
        call(['shp2pgsql -s 4326 clipped.shp public.%s_clipped | psql -h %s -p %s -U %s -d burwell' % (scale, credentials.pg_host, credentials.pg_port, credentials.pg_user)], shell=True)

        # Clean up shapefiles
        call(['rm intersecting.* && rm rgeom.* && rm clipped.*'], shell=True)

        # Build the SQL query
        sql.append("""
        SELECT t.map_id, '%(scale)s' AS scale, t.geom
        FROM carto.flat_%(scale)s t
        LEFT JOIN (
          SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom
          FROM maps.sources
          WHERE scale IN (%(scales_above)s)
        ) sr
        ON ST_Intersects(t.geom, sr.geom)
        WHERE sr.id IS NULL
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
        drop += 'DROP TABLE IF EXISTS %s_clipped;' % scale

    cursor.execute(drop)
    connection.commit()

    end = time.time()
    print 'Created carto.%s in ' % scale, int(end - start), 's'

    # result = cursor.fetchone()
    #
    # primary_table = result[0]
    #
    # # Write it to a shapefile
    # call(['pgsql2shp -f %s.shp -u %s -h %s -p %s burwell sources.%s' % (primary_table, credentials.pg_user, credentials.pg_host, credentials.pg_port, primary_table)], shell=True)
    #
    # # Simplify it with mapshaper
    # call(['mapshaper -i %s.shp -dissolve -o %s_rgeom.shp' % (primary_table, primary_table)], shell=True)
    #
    # # Import the simplified geometry into PostGIS
    # call(['shp2pgsql -s 4326 %s_rgeom.shp public.%s_rgeom | psql -h %s -p %s -U %s -d burwell' % (primary_table, primary_table, credentials.pg_host, credentials.pg_port, credentials.pg_user)], shell=True)
    #
    # # Update the sources table
    # cursor.execute("""
    #     UPDATE maps.sources
    #     SET rgeom = (
    #         SELECT ST_MakeValid(geom)
    #         FROM public.%(primary_table)s
    #     )
    #     WHERE source_id = %(source_id)s
    # """, {
    #     "primary_table": AsIs(primary_table + '_rgeom'),
    #     "source_id": arguments.source_id
    # })
    # connection.commit()
    #
    # # Drop the temporary table
    # cursor.execute("""
    #     DROP TABLE public.%(primary_table)s
    # """, {
    #     "primary_table": AsIs(primary_table + '_rgeom')
    # })
    # connection.commit()
    #
    # # Clean up the working directory
    # call(['rm %s*' % (primary_table, )], shell=True)
    #
    # end = time.time()
    #
    # print 'Done in ', int(end - start), 's'