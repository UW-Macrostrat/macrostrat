from subprocess import call
import os
from psycopg2.extensions import AsIs
from psycopg2.extras import NamedTupleCursor
import yaml
# Load the credentials file
with open(os.path.join(os.path.dirname(__file__), '../../../credentials.yml'), 'r') as f:
    credentials = yaml.load(f)


class RGeom:
    meta = {
        'mariadb': False,
        'pg': True,
        'usage': """
            Populates the field `rgeom` for a given geologic map source.
            The rgeom is a convex hull of all polyons in the source.
        """,
        'required_args': {
            'source_id': 'A valid source_id'
        }
    }
    def __init__(self, pgConnection):
        RGeom.connection = pgConnection()
        RGeom.cursor = RGeom.connection.cursor(cursor_factory = NamedTupleCursor)

    @staticmethod
    def build(source_id):
        # Get the name of the primary table
        RGeom.cursor.execute("""
            SELECT primary_table
            FROM maps.sources
            WHERE source_id = %(source_id)s
        """, {
            'source_id': source_id
        })

        result = RGeom.cursor.fetchone()

        primary_table = result[0]

        FNULL = open(os.devnull, 'w')

        # Clean up
        call(['rm %s.*' % (primary_table ,)], shell=True, stdout=FNULL)
        call(['rm %s_rgeom.*' % (primary_table, )], shell=True, stdout=FNULL)

        # Drop the temporary table
        RGeom.cursor.execute("""
            DROP TABLE IF EXISTS public.%(primary_table)s
        """, {
            'primary_table': AsIs(primary_table + '_rgeom')
        })
        RGeom.connection.commit()

        # Write it to a shapefile
        call(['pgsql2shp -f %s.shp -u %s -h %s -p %s burwell sources.%s' % (primary_table, credentials['pg_user'], credentials['pg_host'], credentials['pg_port'], primary_table)], shell=True, stdout=FNULL)

        # Simplify it with mapshaper
        call(['mapshaper -i %s.shp -dissolve -o %s_rgeom.shp' % (primary_table, primary_table)], shell=True, stdout=FNULL)

        # Import the simplified geometry into PostGIS
        call(['shp2pgsql -s 4326 -I %s_rgeom.shp public.%s_rgeom | psql -h %s -p %s -U %s -d burwell' % (primary_table, primary_table, credentials['pg_host'], credentials['pg_port'], credentials['pg_user'])], shell=True, stdout=FNULL)

        print '     Validating geometry...'
        RGeom.cursor.execute("""
            ALTER TABLE public.%(primary_table)s ALTER COLUMN geom SET DATA TYPE geometry;

            UPDATE public.%(primary_table)s
            SET geom = ST_Buffer(geom, 0);
        """, {
            "primary_table": AsIs(primary_table + '_rgeom')
        })
        RGeom.connection.commit()

        print '     Processing geometry...'
        # Update the sources table
        RGeom.cursor.execute("""
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
                SELECT ST_Union(geom) FROM (
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
            'primary_table': AsIs(primary_table + '_rgeom'),
            'source_id': source_id
        })
        RGeom.connection.commit()

        # Drop the temporary table
        RGeom.cursor.execute("""
            DROP TABLE public.%(primary_table)s
        """, {
            'primary_table': AsIs(primary_table + '_rgeom')
        })
        RGeom.connection.commit()

        # Clean up the working directory
        call(['rm %s*' % (primary_table, )], shell=True)
