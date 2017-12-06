'''
@input
  - source_id

+ Cut target source's footprint out of carto table

+ Create a new temp table to hold the intermediate product to speed up inserts

+ Get all polygons from the underlying scale that intersect the target source's footprint
  - Group by priority
    - Order by priority ASC
    - Cut a hole in the built up polygons equal to the group
    - Insert each group

+ Do the same for the target scale

+ Insert all from the temp table into the carto table
'''
from psycopg2.extensions import AsIs
from psycopg2.extras import NamedTupleCursor

class Carto:
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
        'medium': ['small', 'medium', 'large'],
        'large': ['large']
    }
    source_id = None
    connection = None
    cursor = None

    def __init__(self, pgConnection):
        Carto.connection = pgConnection()
        Carto.cursor = Carto.connection.cursor(cursor_factory = NamedTupleCursor)

    @classmethod
    def insert_scale(cls, scale):
        Carto.cursor.execute("""
            SELECT DISTINCT sa.new_priority
            FROM maps.sources sa
            JOIN maps.sources sb ON ST_Intersects(sa.rgeom, sb.rgeom)
            WHERE sb.source_id = %(source_id)s
            ORDER BY new_priority ASC
        """, { 'source_id': Carto.source_id })

        sources = Carto.cursor.fetchall()

        for row in sources:
            '''
                1. Chop out a spot for the geometries we will insert (cookie cutter)
                2. Remove empty geometries
                3. Insert new geometries
            '''
            Carto.cursor.execute("""
                WITH first AS (
                    SELECT (ST_Dump(ST_Intersection(sb.rgeom, COALESCE(ST_Union(x.rgeom), 'POLYGON EMPTY')))).geom AS geom
                    FROM maps.sources x
                    JOIN maps.sources sb ON ST_Intersects(x.rgeom, sb.rgeom)
                    WHERE sb.source_id = %(source_id)s AND
                      x.new_priority = %(priority)s AND %(scale)s::text = ANY(x.display_scales)
                    GROUP BY sb.rgeom
                )
                UPDATE carto_temp
                SET geom = ST_Difference(carto_temp.geom, q.geom)
                FROM first q
                    WHERE ST_Intersects(carto_temp.geom, q.geom);
            """, {
                'source_id': Carto.source_id,
                'priority': row.new_priority,
                'scale': scale
            })
            Carto.connection.commit()

            Carto.cursor.execute("""
                DELETE FROM carto_temp WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON');
            """)
            Carto.connection.commit()

            Carto.cursor.execute("""
                INSERT INTO carto_temp
                SELECT
                  m.map_id,
                  m.source_id,
                  'tiny'::text AS scale,
                  (ST_Dump(ST_SetSRID(COALESCE(ST_Intersection(m.geom, sb.rgeom), 'POLYGON EMPTY'), 4326))).geom AS geom
                FROM maps.tiny m
                JOIN maps.sources sa ON m.source_id = sa.source_id
                JOIN maps.sources sb ON ST_Intersects(m.geom, sb.rgeom)
                WHERE sb.source_id = %(source_id)s AND sa.new_priority = %(priority)s AND %(scale)s::text = ANY(sa.display_scales);
            """, {
                'source_id': Carto.source_id,
                'priority': row.new_priority,
                'scale': scale
            })

            Carto.cursor.execute("""
                INSERT INTO carto_temp
                SELECT
                  m.map_id,
                  m.source_id,
                  'small'::text AS scale,
                  (ST_Dump(ST_SetSRID(COALESCE(ST_Intersection(m.geom, sb.rgeom), 'POLYGON EMPTY'), 4326))).geom AS geom
                FROM maps.small m
                JOIN maps.sources sa ON m.source_id = sa.source_id
                JOIN maps.sources sb ON ST_Intersects(m.geom, sb.rgeom)
                WHERE sb.source_id = %(source_id)s AND sa.new_priority = %(priority)s AND %(scale)s::text = ANY(sa.display_scales);
            """, {
                'source_id': Carto.source_id,
                'priority': row.new_priority,
                'scale': scale
            })

            Carto.cursor.execute("""
                INSERT INTO carto_temp
                SELECT
                  m.map_id,
                  m.source_id,
                  'medium'::text AS scale,
                  (ST_Dump(ST_SetSRID(COALESCE(ST_Intersection(m.geom, sb.rgeom), 'POLYGON EMPTY'), 4326))).geom AS geom
                FROM maps.medium m
                JOIN maps.sources sa ON m.source_id = sa.source_id
                JOIN maps.sources sb ON ST_Intersects(m.geom, sb.rgeom)
                WHERE sb.source_id = %(source_id)s AND sa.new_priority = %(priority)s AND %(scale)s::text = ANY(sa.display_scales);
            """, {
                'source_id': Carto.source_id,
                'priority': row.new_priority,
                'scale': scale
            })

            Carto.cursor.execute("""
                INSERT INTO carto_temp
                SELECT
                  m.map_id,
                  m.source_id,
                  'large'::text AS scale,
                  (ST_Dump(ST_SetSRID(COALESCE(ST_Intersection(m.geom, sb.rgeom), 'POLYGON EMPTY'), 4326))).geom AS geom
                FROM maps.large m
                JOIN maps.sources sa ON m.source_id = sa.source_id
                JOIN maps.sources sb ON ST_Intersects(m.geom, sb.rgeom)
                WHERE sb.source_id = %(source_id)s AND sa.new_priority = %(priority)s AND %(scale)s::text = ANY(sa.display_scales);
            """, {
                'source_id': Carto.source_id,
                'priority': row.new_priority,
                'scale': scale
            })

            Carto.cursor.execute("""
                DELETE FROM carto_temp WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON');
            """)
            Carto.connection.commit()


    @classmethod
    def processScale(cls, the_scale):
        SCALE_UNDER = Carto.UNDER[the_scale]
        print the_scale

        print '   1. Clean and create'
        Carto.cursor.execute("""
            DROP TABLE IF EXISTS carto_temp;
            CREATE TABLE carto_temp AS SELECT * FROM carto_new.%(scale)s LIMIT 0;
            CREATE INDEX ON carto_temp USING GiST (geom);
        """, { 'scale': AsIs(the_scale) })
        Carto.connection.commit()

        '''
        + Get all polygons from the underlying scale that intersect the target source's footprint
        - Group by priority
          - Order by priority ASC
          - Cut a hole in the built up polygons equal to the group
          - Insert each group
        '''
        print '   2. Scale under'
        if SCALE_UNDER is not None:
            Carto.insert_scale(SCALE_UNDER)

        print '   3. Scale'
        Carto.insert_scale(the_scale)

        '''
            Cut target source's footprint out of carto table
        '''
        print '   4. Cut'
        Carto.cursor.execute("""
            UPDATE carto_new.%(scale)s
            SET geom = ST_Difference(geom, rgeom)
            FROM maps.sources
            WHERE ST_Intersects(geom, rgeom) AND sources.source_id = %(source)s;
        """, {
            'source': Carto.source_id,
            'scale': AsIs(the_scale)
        })

        Carto.cursor.execute("""
            DELETE FROM carto_new.%(scale)s
            WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON');
        """, {
            'scale': AsIs(the_scale)
        })

        print '   5. Insert'
        Carto.cursor.execute("""
            INSERT INTO carto_new.%(scale)s (map_id, source_id, scale, geom)
            SELECT * FROM carto_temp;
        """, {
            'scale': AsIs(the_scale)
        })

        print '   6. Clean up'
        Carto.cursor.execute("""
            DROP TABLE carto_temp;
        """)
        Carto.connection.commit()

        print '   7. Clean up bad geometries'
        Carto.cursor.execute("""
            DELETE FROM carto_new.%(scale)s
            WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON');
        """, {
            'scale': AsIs(the_scale)
        })
        Carto.connection.commit()


    @staticmethod
    def build(source_id):
        Carto.source_id = source_id

        Carto.cursor.execute("""
            SELECT display_scales
            FROM maps.sources
            WHERE source_id = %(source_id)s
        """, { 'source_id': source_id })
        scales = Carto.cursor.fetchone()

        if len(scales) == 0 or scales is None:
            print 'Source not found'
            sys.exit()

        allScales = [ Carto.scaleIsIn[scale] for scale in scales[0] ]
        scales = set([ scale for scales in allScales for scale in scales ])

        print 'Scales to refresh: '
        for scale in scales:
            print scale

        for scale in scales:
            Carto.processScale(scale)
