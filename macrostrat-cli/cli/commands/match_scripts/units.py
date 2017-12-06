from psycopg2.extensions import AsIs
from psycopg2.extras import RealDictCursor
import time
import datetime
import sys

class Units:
    meta = {
        'mariadb': False,
        'pg': True,
        'usage': """
            Matches burwell polygons to macrostrat units
        """,
        'required_args': {
            'source_id': 'A valid source_id'
        }
    }

    source_id = None
    table = None
    field = None
    connection = None
    cursor = None

    def __init__(self, pgConnection):
        Units.connection = pgConnection()
        Units.cursor = Units.connection.cursor(cursor_factory = RealDictCursor)


    @classmethod
    def query_down(self, strictNameMatch, strictSpace, strictTime):
        match_type = self.field

        if not strictNameMatch:
            match_type += '_fname'

        if not strictSpace:
            match_type += '_fspace'

        if not strictTime:
            match_type += '_ftime'

        Units.cursor.execute("""
          INSERT INTO maps.map_units (map_id, unit_id, basis_col)
            WITH a AS (
              SELECT map_id, lookup_strat_names.strat_name_id, q.age_top, q.age_bottom, geom
              FROM macrostrat.lookup_strat_names
              JOIN (
                SELECT DISTINCT ON (m.map_id, concept_id) m.map_id, concept_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
                FROM maps.%(table)s m
                JOIN macrostrat.intervals intervals_top on m.t_interval = intervals_top.id
                JOIN macrostrat.intervals intervals_bottom on m.b_interval = intervals_bottom.id
                JOIN maps.map_strat_names ON m.map_id = map_strat_names.map_id
                JOIN macrostrat.lookup_strat_names on map_strat_names.strat_name_id = lookup_strat_names.strat_name_id
                WHERE m.source_id = %(source_id)s
                AND basis_col = %(match_type)s
                AND m.map_id NOT IN (
                  SELECT x.map_id
                  FROM maps.map_units x
                  JOIN maps.%(table)s z
                  ON x.map_id = z.map_id
                  WHERE z.source_id = %(source_id)s
                )
              ) q ON q.concept_id = lookup_strat_names.concept_id
            ),
            shaped AS (
              SELECT strat_name_id, strat_name, rank,
                CASE
                    WHEN rank = 'Bed'
                      THEN '{}'
                    WHEN rank = 'Mbr'
                      THEN (SELECT COALESCE(array_agg(DISTINCT strat_name_id), '{}') FROM macrostrat.lookup_strat_names WHERE rank = 'Bed' AND mbr_id = lsn.strat_name_id)
                    WHEN rank = 'Fm'
                      THEN (SELECT COALESCE(array_agg(DISTINCT strat_name_id), '{}') FROM macrostrat.lookup_strat_names WHERE rank IN ('Bed', 'Mbr') AND fm_id = lsn.strat_name_id)
                    WHEN rank = 'Gp'
                      THEN (SELECT COALESCE(array_agg(DISTINCT strat_name_id), '{}') FROM macrostrat.lookup_strat_names WHERE rank IN ('Bed', 'Mbr', 'Fm') AND gp_id = lsn.strat_name_id)
                    WHEN rank = 'SGp'
                      THEN (SELECT COALESCE(array_agg(DISTINCT strat_name_id), '{}') FROM macrostrat.lookup_strat_names WHERE rank IN ('Bed', 'Mbr', 'Fm', 'Gp') AND sgp_id = lsn.strat_name_id)
                  END AS down
              FROM macrostrat.lookup_strat_names lsn
            ),
            flattened AS (
              SELECT strat_name_id, strat_name, rank, unnest(down) as down_names
              FROM shaped s
            ),
            b AS (
            SELECT
              flattened.strat_name_id AS match_strat_name_id,
              flattened.strat_name AS match_strat_name,
              flattened.rank AS match_rank,
              lookup_strat_names.strat_name,
              unit_strat_names.strat_name_id,
              unit_strat_names.unit_id,
              lookup_unit_intervals.t_age,
              lookup_unit_intervals.b_age,
              """ + ("cols.poly_geom " if strictSpace else "st_buffer(st_envelope(cols.poly_geom), 1.2)") + """ AS geom
            FROM macrostrat.unit_strat_names
            JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
            JOIN macrostrat.cols ON units_sections.col_id = cols.id
            JOIN macrostrat.lookup_unit_intervals ON unit_strat_names.unit_id = lookup_unit_intervals.unit_id
            JOIN flattened ON flattened.down_names = unit_strat_names.strat_name_id
            JOIN macrostrat.lookup_strat_names ON flattened.down_names = lookup_strat_names.strat_name_id
            )
            SELECT DISTINCT ON (map_id, b.unit_id) map_id, b.unit_id AS units, %(match_type)s
            FROM a
            JOIN b ON a.strat_name_id = b.match_strat_name_id
            WHERE ST_Intersects(a.geom, b.geom)
                AND ((b.t_age) < (a.age_bottom + """ + ("0" if strictTime else "25") + """))
                AND ((b.b_age) > (a.age_top - """ + ("0" if strictTime else "25") + """));
        """, {
          'table': AsIs(self.table),
          'source_id': self.source_id,
          'field': AsIs(self.field),
          'match_type': match_type
        })

        Units.connection.commit()

        print '        - Done with %s (up)' % (match_type, )

    @classmethod
    def query_up(self, strictNameMatch, strictSpace, strictTime):
        match_type = self.field

        if not strictNameMatch:
            match_type += '_fname'

        if not strictSpace:
            match_type += '_fspace'

        if not strictTime:
            match_type += '_ftime'

        Units.cursor.execute("""
          INSERT INTO maps.map_units (map_id, unit_id, basis_col)
            WITH a AS (
              SELECT map_id, lookup_strat_names.strat_name_id, q.age_top, q.age_bottom, geom
              FROM macrostrat.lookup_strat_names
              JOIN (
                SELECT DISTINCT ON (m.map_id, concept_id) m.map_id, concept_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
                FROM maps.%(table)s m
                JOIN macrostrat.intervals intervals_top on m.t_interval = intervals_top.id
                JOIN macrostrat.intervals intervals_bottom on m.b_interval = intervals_bottom.id
                JOIN maps.map_strat_names ON m.map_id = map_strat_names.map_id
                JOIN macrostrat.lookup_strat_names on map_strat_names.strat_name_id = lookup_strat_names.strat_name_id
                WHERE m.source_id = %(source_id)s
                AND basis_col = %(match_type)s
                AND m.map_id NOT IN (
                  SELECT x.map_id
                  FROM maps.map_units x
                  JOIN maps.%(table)s z
                  ON x.map_id = z.map_id
                  WHERE z.source_id = %(source_id)s
                )
              ) q ON q.concept_id = lookup_strat_names.concept_id
            ),
            shaped AS (
              SELECT strat_name_id, strat_name, rank,
              (SELECT COALESCE(array_agg(u), '{}')
                FROM unnest(
                CASE
                  WHEN rank = 'Bed'
                    THEN array[mbr_id, fm_id, gp_id, sgp_id]
                  WHEN rank = 'Mbr'
                    THEN array[fm_id, gp_id, sgp_id]
                  WHEN rank = 'Fm'
                    THEN array[gp_id, sgp_id]
                  WHEN rank = 'Gp'
                    THEN array[sgp_id]
                  WHEN rank = 'SGp'
                    THEN '{}'
                END
                ) AS u WHERE u != 0
              ) AS up
              FROM macrostrat.lookup_strat_names lsn
            ),
            flattened AS (
              SELECT strat_name_id, strat_name, rank, unnest(up) as up_names
              FROM shaped s
            ),
            b AS (
            SELECT
              flattened.strat_name_id AS match_strat_name_id,
              flattened.strat_name AS match_strat_name,
              flattened.rank AS match_rank,
              lookup_strat_names.strat_name,
              unit_strat_names.strat_name_id,
              unit_strat_names.unit_id,
              lookup_unit_intervals.t_age,
              lookup_unit_intervals.b_age,
              """ + ("cols.poly_geom " if strictSpace else "st_buffer(st_envelope(cols.poly_geom), 1.2)") + """ AS geom
            FROM macrostrat.unit_strat_names
            JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
            JOIN macrostrat.cols ON units_sections.col_id = cols.id
            JOIN macrostrat.lookup_unit_intervals ON unit_strat_names.unit_id = lookup_unit_intervals.unit_id
            JOIN flattened ON flattened.up_names = unit_strat_names.strat_name_id
            JOIN macrostrat.lookup_strat_names ON flattened.up_names = lookup_strat_names.strat_name_id
            )
            SELECT DISTINCT ON (map_id, b.unit_id) map_id, b.unit_id AS units, %(match_type)s
            FROM a
            JOIN b ON a.strat_name_id = b.match_strat_name_id
            WHERE ST_Intersects(a.geom, b.geom)
                AND ((b.t_age) < (a.age_bottom + """ + ("0" if strictTime else "25") + """))
                AND ((b.b_age) > (a.age_top - """ + ("0" if strictTime else "25") + """));
        """, {
          'table': AsIs(self.table),
          'source_id': self.source_id,
          'field': AsIs(self.field),
          'match_type': match_type
        })

        Units.connection.commit()

        print '        - Done with %s (down)' % (match_type, )


    @classmethod
    def query(self, strictNameMatch, strictSpace, strictTime):
        match_type = self.field

        if not strictNameMatch:
            match_type += '_fname'

        if not strictSpace:
            match_type += '_fspace'

        if not strictTime:
            match_type += '_ftime'

        Units.cursor.execute("""
            INSERT INTO maps.map_units (map_id, unit_id, basis_col)
            WITH a AS (
               SELECT map_id, lookup_strat_names.strat_name_id, q.age_top, q.age_bottom, geom
              FROM macrostrat.lookup_strat_names
              JOIN (
                SELECT DISTINCT ON (m.map_id, concept_id) m.map_id, concept_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
                FROM maps.%(table)s m
                JOIN macrostrat.intervals intervals_top on m.t_interval = intervals_top.id
                JOIN macrostrat.intervals intervals_bottom on m.b_interval = intervals_bottom.id
                JOIN maps.map_strat_names ON m.map_id = map_strat_names.map_id
                JOIN macrostrat.lookup_strat_names on map_strat_names.strat_name_id = lookup_strat_names.strat_name_id
                WHERE m.source_id = %(source_id)s
                AND basis_col = %(match_type)s
                AND m.map_id NOT IN (
                  SELECT x.map_id
                  FROM maps.map_units x
                  JOIN maps.%(table)s z
                  ON x.map_id = z.map_id
                  WHERE z.source_id = %(source_id)s
                )
              ) q ON q.concept_id = lookup_strat_names.concept_id
            ),
            b AS (
              SELECT unit_strat_names.strat_name_id, unit_strat_names.unit_id, lookup_unit_intervals.t_age, lookup_unit_intervals.b_age, """ + ("cols.poly_geom " if strictSpace else "st_buffer(st_envelope(cols.poly_geom), 1.2)") + """ AS geom
              FROM macrostrat.unit_strat_names
              JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
              JOIN macrostrat.cols ON units_sections.col_id = cols.id
              JOIN macrostrat.lookup_unit_intervals ON unit_strat_names.unit_id = lookup_unit_intervals.unit_id
              WHERE strat_name_id IN (SELECT DISTINCT strat_name_id FROM a)
            )
            SELECT DISTINCT ON (map_id, b.unit_id) map_id, b.unit_id AS units, %(match_type)s
            FROM a
            JOIN b ON a.strat_name_id = b.strat_name_id
            WHERE ST_Intersects(a.geom, b.geom)
                AND ((b.t_age) < (a.age_bottom + """ + ("0" if strictTime else "25") + """))
                AND ((b.b_age) > (a.age_top - """ + ("0" if strictTime else "25") + """));
        """, {
          'table': AsIs(self.table),
          'source_id': self.source_id,
          'field': AsIs(self.field),
          'match_type': match_type
        })

        Units.connection.commit()

        print '        - Done with %s' % (match_type, )


    @classmethod
    def match(self) :
        # strictName, strictSpace, strictTime, useNullSet

        # Strict name, strict space, strict time
        a = Units.query(True, True, True)

        # Strict name, fuzzy space, strict time
        b = Units.query(True, False, True)

        # Fuzzy name, strict space, strict time
        c = Units.query(False, True, True)

        # Strict name, strict space, fuzzy time
        d = Units.query(True, True, False)

        # Fuzzy name, fuzzy space, strict time
        e = Units.query(False, False, True)

        # Strict name, fuzzy space, fuzzy time
        f = Units.query(True, False, False)

        # Fuzzy name, strict space, fuzzy time
        g = Units.query(False, True, False)

        # Fuzzy name, fuzzy space, fuzzy time
        h = Units.query(False, False, False)

    @classmethod
    def match_down(self):
        # strictName, strictSpace, strictTime, useNullSet

        # Strict name, strict space, strict time
        a = Units.query_down(True, True, True)

        # Strict name, fuzzy space, strict time
        b = Units.query_down(True, False, True)

        # Fuzzy name, strict space, strict time
        c = Units.query_down(False, True, True)

        # Strict name, strict space, fuzzy time
        d = Units.query_down(True, True, False)

        # Fuzzy name, fuzzy space, strict time
        e = Units.query_down(False, False, True)

        # Strict name, fuzzy space, fuzzy time
        f = Units.query_down(True, False, False)

        # Fuzzy name, strict space, fuzzy time
        g = Units.query_down(False, True, False)

        # Fuzzy name, fuzzy space, fuzzy time
        h = Units.query_down(False, False, False)


    @classmethod
    def match_up(self):
        # strictName, strictSpace, strictTime

        # Strict name, strict space, strict time
        a = Units.query_up(True, True, True)

        # Strict name, fuzzy space, strict time
        b = Units.query_up(True, False, True)

        # Fuzzy name, strict space, strict time
        c = Units.query_up(False, True, True)

        # Strict name, strict space, fuzzy time
        d = Units.query_up(True, True, False)

        # Fuzzy name, fuzzy space, strict time
        e = Units.query_up(False, False, True)

        # Strict name, fuzzy space, fuzzy time
        f = Units.query_up(True, False, False)

        # Fuzzy name, strict space, fuzzy time
        g = Units.query_up(False, True, False)

        # Fuzzy name, fuzzy space, fuzzy time
        h = Units.query_up(False, False, False)


    @classmethod
    def do_work(self, field):
        # Time the process
        start_time = time.time()

        print '      * Working on ', field, ' *'

        self.field = field

        Units.match()
        Units.match_down()
        Units.match_up()


        elapsed = int(time.time() - start_time)
        print '        Done with ', self.field, ' in ', elapsed / 60, ' minutes and ', elapsed % 60, ' seconds'


    @staticmethod
    def build(source_id):
        Units.source_id = source_id
        # Validate params!
        # Valid source_id
        Units.cursor.execute('''
            SELECT source_id
            FROM maps.sources
            WHERE source_id = %(source_id)s
        ''', {
            'source_id': source_id
        })
        result = Units.cursor.fetchone()
        if result is None:
            print 'Invalid source_id. %s was not found in maps.sources' % (source_id, )
            sys.exit(1)

        # Find scale table
        scale = ''
        for scale_table in ['tiny', 'small', 'medium', 'large']:
          Units.cursor.execute('''
            SELECT *
            FROM maps.%(table)s
            WHERE source_id = %(source_id)s
            LIMIT 1
        ''', {
            'table': AsIs(scale_table),
            'source_id': source_id
          })
          if Units.cursor.fetchone() is not None:
            scale = scale_table
            break

        if len(scale) == 0:
          print 'Provided source_id not found in maps.small, maps.medium, or maps.large. Please insert it and try again.'
          sys.exit(1)

        # TODO cleanup this jank assignment
        Units.table = scale

        print 'Starting at ', str(datetime.datetime.now())


        # Clean up
        Units.cursor.execute("""
          DELETE FROM maps.map_units
          WHERE map_id IN (
            SELECT map_id
            FROM maps.%(table)s
            WHERE source_id = %(source_id)s
          )
          AND basis_col NOT LIKE 'manual%%'
        """, {
          'table': AsIs(scale),
          'source_id': source_id
        })

        Units.connection.commit()
        print '        + Done cleaning up'


        # Fields in burwell to match on
        fields = ['strat_name', 'name', 'descrip', 'comments']

        # Filter null fields
        Units.cursor.execute("""
        SELECT
            count(distinct strat_name)::int AS strat_name,
            count(distinct name)::int AS name,
            count(distinct descrip)::int AS descrip,
            count(distinct comments)::int AS comments
        FROM maps.%(scale)s where source_id = %(source_id)s;
        """, {
            'scale': AsIs(scale),
            'source_id': source_id
        })
        result = Units.cursor.fetchone()

        for field in fields:

            if result[field] == 0:
                fields.remove(field)
                print '        + Excluding %s because it is null' % (field, )


        # Insert a new task for each matching field into the queue
        for field in fields:
            Units.do_work(field)
