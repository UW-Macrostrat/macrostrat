import time
from ..base import Base
from psycopg2.extensions import AsIs
import sys

class Carto(Base):
    """
    macrostrat process carto <source_id>:
        Inserts/updates a given map source's polygons into the appropriate carto tables
        NB: Updates the tables in the schema `carto_new`
        Processes as follows:
            + Cut target source's footprint out of the appropriate carto table
            + Create a new temp table to hold the intermediate product to speed up inserts
            + Get all polygons from the underlying scale that intersect the target source's footprint
              - Group by priority
                - Order by priority ASC
                - Cut a hole in the built up polygons equal to the group
                - Insert each group
            + Do the same for the target scale
            + Insert all from the temp table into the carto table

    Usage:
      macrostrat process carto <source_id>
      macrostrat process carto -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat process carto 123
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """
    meta = {
        'mariadb': False,
        'pg': True,
        'usage': """
            Adds a given source to the proper carto tables.
        """,
        'required_args': {
            'source_id': 'A valid source_id'
        }
    }
    UNDER = {
        'small': 'tiny',
        'medium': 'small',
        'large': 'medium'
    }
    scaleIsIn = {
        'tiny': ['tiny'],
        'small': ['small', 'medium'],
        'medium': ['medium', 'large'],
        'large': ['large']
    }
    source_id = None

    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)


    def insert_scale(self, scale):
        # Get a list of unique priorities that overlap with this source
        self.pg['cursor'].execute("""
            WITH dumped AS (
                SELECT source_id, new_priority, (ST_Dump(rgeom)).geom
                FROM maps.sources
            )
            SELECT DISTINCT sa.new_priority
            FROM dumped sa
            JOIN dumped sb ON ST_Intersects(sa.geom, sb.geom)
            WHERE sb.source_id = %(source_id)s
            ORDER BY new_priority ASC
        """, { 'source_id': Carto.source_id })

        sources = self.pg['cursor'].fetchall()

        for row in sources:
            '''
                1. Chop out a spot for the geometries we will insert (cookie cutter)
                2. Remove empty geometries
                3. Insert new geometries
            '''
            self.pg['cursor'].execute("""
                WITH first AS (
                    SELECT (ST_Dump(ST_Intersection(sb.rgeom, COALESCE(ST_Union(x.rgeom), 'POLYGON EMPTY')))).geom AS geom
                    FROM maps.sources x
                    JOIN maps.sources sb ON ST_Intersects(x.rgeom, sb.rgeom)
                    WHERE sb.source_id = %(source_id)s AND
                      x.new_priority = %(priority)s AND %(scale)s::text = ANY(x.display_scales)
                    GROUP BY sb.rgeom
                )
                UPDATE carto_temp
                SET geom =
                    CASE
                        WHEN ST_Contains(q.geom, carto_temp.geom)
                            THEN 'POLYGON EMPTY'
                        ELSE ST_Difference(carto_temp.geom, q.geom)
                    END
                FROM first q
                    WHERE ST_Intersects(carto_temp.geom, q.geom);
            """, {
                'source_id': Carto.source_id,
                'priority': row.new_priority,
                'scale': scale
            })
            self.pg['connection'].commit()

            self.pg['cursor'].execute("""
                DELETE FROM carto_temp WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON') OR ST_IsEmpty(geom);;
            """)
            self.pg['connection'].commit()

            self.pg['cursor'].execute("""
                INSERT INTO carto_temp
                SELECT
                  m.map_id,
                  m.source_id,
                  'tiny'::text AS scale,
                  (ST_Dump(ST_SetSRID(COALESCE(CASE
                    WHEN ST_Contains(sb.rgeom, m.geom)
                        THEN m.geom
                    ELSE
                        ST_Intersection(m.geom, sb.rgeom)
                    END, 'POLYGON EMPTY'), 4326))).geom AS geom
                FROM maps.tiny m
                JOIN maps.sources sa ON m.source_id = sa.source_id
                JOIN maps.sources sb ON ST_Intersects(m.geom, sb.rgeom)
                WHERE sb.source_id = %(source_id)s AND sa.new_priority = %(priority)s AND %(scale)s::text = ANY(sa.display_scales);
            """, {
                'source_id': Carto.source_id,
                'priority': row.new_priority,
                'scale': scale
            })

            self.pg['cursor'].execute("""
                INSERT INTO carto_temp
                SELECT
                  m.map_id,
                  m.source_id,
                  'small'::text AS scale,
                  (ST_Dump(ST_SetSRID(COALESCE(CASE
                    WHEN ST_Contains(sb.rgeom, m.geom)
                        THEN m.geom
                    ELSE
                        ST_Intersection(m.geom, sb.rgeom)
                    END, 'POLYGON EMPTY'), 4326))).geom AS geom
                FROM maps.small m
                JOIN maps.sources sa ON m.source_id = sa.source_id
                JOIN maps.sources sb ON ST_Intersects(m.geom, sb.rgeom)
                WHERE sb.source_id = %(source_id)s AND sa.new_priority = %(priority)s AND %(scale)s::text = ANY(sa.display_scales);
            """, {
                'source_id': Carto.source_id,
                'priority': row.new_priority,
                'scale': scale
            })

            self.pg['cursor'].execute("""
                INSERT INTO carto_temp
                SELECT
                  m.map_id,
                  m.source_id,
                  'medium'::text AS scale,
                  (ST_Dump(ST_SetSRID(COALESCE(CASE
                    WHEN ST_Contains(sb.rgeom, m.geom)
                        THEN m.geom
                    ELSE
                        ST_Intersection(m.geom, sb.rgeom)
                    END, 'POLYGON EMPTY'), 4326))).geom AS geom
                FROM maps.medium m
                JOIN maps.sources sa ON m.source_id = sa.source_id
                JOIN maps.sources sb ON ST_Intersects(m.geom, sb.rgeom)
                WHERE sb.source_id = %(source_id)s AND sa.new_priority = %(priority)s AND %(scale)s::text = ANY(sa.display_scales);
            """, {
                'source_id': Carto.source_id,
                'priority': row.new_priority,
                'scale': scale
            })

            self.pg['cursor'].execute("""
                INSERT INTO carto_temp
                SELECT
                  m.map_id,
                  m.source_id,
                  'large'::text AS scale,
                  (ST_Dump(ST_SetSRID(COALESCE(CASE
                    WHEN ST_Contains(sb.rgeom, m.geom)
                        THEN m.geom
                    ELSE
                        ST_Intersection(m.geom, sb.rgeom)
                    END, 'POLYGON EMPTY'), 4326))).geom AS geom
                FROM maps.large m
                JOIN maps.sources sa ON m.source_id = sa.source_id
                JOIN maps.sources sb ON ST_Intersects(m.geom, sb.rgeom)
                WHERE sb.source_id = %(source_id)s AND sa.new_priority = %(priority)s AND %(scale)s::text = ANY(sa.display_scales);
            """, {
                'source_id': Carto.source_id,
                'priority': row.new_priority,
                'scale': scale
            })

            self.pg['cursor'].execute("""
                DELETE FROM carto_temp WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON') OR ST_IsEmpty(geom);;
            """)
            self.pg['connection'].commit()


    def processScale(self, the_scale):
        SCALE_UNDER = Carto.UNDER[the_scale]
        print the_scale

        print '   1. Clean and create'
        self.pg['cursor'].execute("""
            DROP TABLE IF EXISTS carto_temp;
            CREATE TABLE carto_temp AS SELECT * FROM carto_new.%(scale)s LIMIT 0;
            CREATE INDEX ON carto_temp USING GiST (geom);
        """, { 'scale': AsIs(the_scale) })
        self.pg['connection'].commit()

        '''
        + Get all polygons from the underlying scale that intersect the target source's footprint
        - Group by priority
          - Order by priority ASC
          - Cut a hole in the built up polygons equal to the group
          - Insert each group
        '''
        print '   2. Scale under'
        if SCALE_UNDER is not None:
            Carto.insert_scale(self, SCALE_UNDER)

        print '   3. Scale'
        Carto.insert_scale(self, the_scale)

        '''
            Cut target source's footprint out of carto table
        '''
        print '   4. Cut'
        self.pg['cursor'].execute("""
            DROP TABLE IF EXISTS temp_subdivide;
            CREATE TABLE temp_subdivide
            AS SELECT row_number() OVER() as row_id, rgeom
            FROM (
                SELECT ST_Subdivide(rgeom) as rgeom
                FROM maps.sources
                WHERE source_id = %(source_id)s
            ) foo
        """, { 'source_id': Carto.source_id })
        self.pg['connection'].commit()
        self.pg['cursor'].execute("CREATE INDEX ON temp_subdivide USING GiST (rgeom)")
        self.pg['connection'].commit()

        self.pg['cursor'].execute("SELECT row_id FROM temp_subdivide ORDER BY row_id ASC")
        rows = self.pg['cursor'].fetchall()
        for row in rows:
            self.pg['cursor'].execute("""
                UPDATE carto_new.%(scale)s
                SET geom = ST_Difference(geom, rgeom)
                FROM temp_subdivide
                WHERE ST_Intersects(geom, rgeom)
                    AND row_id = %(row_id)s
            """, {
                'row_id': row.row_id,
                'scale': AsIs(the_scale)
            })
        self.pg['connection'].commit()
        self.pg['cursor'].execute("DROP TABLE temp_subdivide")
        self.pg['connection'].commit()

        self.pg['cursor'].execute("""
            DELETE FROM carto_new.%(scale)s
            WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON') OR ST_IsEmpty(geom);
        """, {
            'scale': AsIs(the_scale)
        })

        print '   5. Insert'
        self.pg['cursor'].execute("""
            INSERT INTO carto_new.%(scale)s (map_id, source_id, scale, geom)
            SELECT * FROM carto_temp;
        """, {
            'scale': AsIs(the_scale)
        })

        print '   6. Clean up'
        self.pg['cursor'].execute("""
            DROP TABLE carto_temp;
        """)
        self.pg['connection'].commit()

        print '   7. Clean up bad geometries'
        self.pg['cursor'].execute("""
            DELETE FROM carto_new.%(scale)s
            WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON') OR ST_IsEmpty(geom);
        """, {
            'scale': AsIs(the_scale)
        })
        self.pg['connection'].commit()


    def build(self, source_id):
        if source_id == '--help' or source_id == '-h':
            print Carto.__doc__
            sys.exit()

        start = time.time()
        Carto.source_id = source_id

        self.pg['cursor'].execute("""
            SELECT display_scales
            FROM maps.sources
            WHERE source_id = %(source_id)s
        """, { 'source_id': source_id })
        scales = self.pg['cursor'].fetchone()

        if len(scales) == 0 or scales is None:
            print 'Source not found'
            sys.exit()

        allScales = [ Carto.scaleIsIn[scale] for scale in scales.display_scales ]
        scales = set([ scale for scales in allScales for scale in scales ])

        print 'Scales to refresh: %s' % (', '.join(scales), )

        for scale in scales:
            Carto.processScale(self, scale)

        end = time.time()
        print 'Took %s' % ((end - start), )
