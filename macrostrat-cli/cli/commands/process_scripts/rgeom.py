from subprocess import call
import os
import sys
from ..base import Base
from psycopg2.extensions import AsIs

class RGeom(Base):
    """
    macrostrat process rgeom <source_id>:
        Populate the field `rgeom` (i.e. "reference geometry") in the table maps.sources
        The rgeom is a convex hull of the given source. However, in order to speed things
        up, the command line tool mapshaper is used to create the initial geometry before
        being processed in PostGIS to remove slivers and small interior rings. The rgeom
        is used for many things, including cutting geometries when creating the carto
        tables.

    Usage:
      macrostrat process rgeom <source_id>
      macrostrat process rgeom -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
      --simple                          Skip geometry ring cleanup
    Examples:
      macrostrat process rgeom 123
      macrostrat process rgeom 123 --simple
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """
    meta = {
        'mariadb': False,
        'pg': True,
        'usage': """
            Populates the field `rgeom` for a given geologic map source.
        """,
        'required_args': {
            'source_id': 'A valid source_id'
        }
    }
    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)

    def run(self, source_id):

        print 'args'
        print self.args
        print '--simple' in self.args[0]
        sys.exit()
        if len(source_id) == 0 or source_id[0] == '--help' or source_id[0] == '-h':
            print RGeom.__doc__
            sys.exit()

        source_id = source_id[0]

        # Get the name of the primary table
        self.pg['cursor'].execute("""
            SELECT scale
            FROM maps.sources
            WHERE source_id = %(source_id)s
        """, {
            'source_id': source_id
        })

        result = self.pg['cursor'].fetchone()

        scale = result[0]
        primary_table = result[0] + str(source_id)

        FNULL = open(os.devnull, 'w')

        # Clean up
        call(['rm %s.*' % (primary_table ,)], shell=True, stdout=FNULL)
        call(['rm %s_rgeom.*' % (primary_table, )], shell=True, stdout=FNULL)

        # Drop the temporary table
        self.pg['cursor'].execute("""
            DROP TABLE IF EXISTS public.%(primary_table)s
        """, {
            'primary_table': AsIs(primary_table + '_rgeom')
        })
        self.pg['connection'].commit()

        # Write it to a shapefile
        call(['pgsql2shp -f %s.shp -u %s -h %s -p %s burwell "SELECT geom FROM maps.%s WHERE source_id = %s" ' % (primary_table, self.credentials['pg_user'], self.credentials['pg_host'], self.credentials['pg_port'], scale, source_id)], shell=True, stdout=FNULL)

        # Simplify it with mapshaper
        call(['mapshaper -i %s.shp -dissolve -o %s_rgeom.shp' % (primary_table, primary_table)], shell=True, stdout=FNULL)

        # Import the simplified geometry into PostGIS
        call(['shp2pgsql -s 4326 -I %s_rgeom.shp public.%s_rgeom | psql -h %s -p %s -U %s -d burwell' % (primary_table, primary_table, self.credentials['pg_host'], self.credentials['pg_port'], self.credentials['pg_user'])], shell=True, stdout=FNULL)

        print '     Validating geometry...'
        self.pg['cursor'].execute("""
            ALTER TABLE public.%(primary_table)s ALTER COLUMN geom SET DATA TYPE geometry;

            UPDATE public.%(primary_table)s
            SET geom = ST_SetSRID(ST_Buffer(ST_MakeValid(geom), 0), 4326);
        """, {
            "primary_table": AsIs(primary_table + '_rgeom')
        })
        self.pg['connection'].commit()

        if '--simple' in self.args[0]:
            self.pg['cursor'].execute("""
                UPDATE maps.sources
                SET rgeom = (
                    SELECT geom
                    FROM public.%primary_table
                )
                WHERE source_id = %(source_id)s
            """, {
                'primary_table': AsIs(primary_table + '_rgeom'),
                'source_id': source_id
            })
            self.pg['connection'].commit()
        else:
            print '     Processing geometry...'
            # Update the sources table
            self.pg['cursor'].execute("""
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
            self.pg['connection'].commit()

        # Drop the temporary table
        self.pg['cursor'].execute("""
            DROP TABLE public.%(primary_table)s
        """, {
            'primary_table': AsIs(primary_table + '_rgeom')
        })
        self.pg['connection'].commit()

        # Clean up the working directory
        call(['rm %s*' % (primary_table, )], shell=True)
