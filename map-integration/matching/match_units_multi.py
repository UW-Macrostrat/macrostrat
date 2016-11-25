# Adapted/borrowed from http://stackoverflow.com/a/7556042/1956065
import multiprocessing
import psycopg2
from psycopg2.extensions import AsIs
import time
import sys
import os

sys.path = [os.path.join(os.path.dirname(__file__), os.pardir)] + sys.path
import credentials


class Processor(multiprocessing.Process):

  def __init__(self, task_queue, result_queue):
    multiprocessing.Process.__init__(self)
    self.task_queue = task_queue
    self.result_queue = result_queue
    self.pyConn = psycopg2.connect(dbname=credentials.pg_db, user=credentials.pg_user, host=credentials.pg_host, port=credentials.pg_port)
    self.pyConn.set_isolation_level(0)


  def run(self):
    proc_name = self.name
    while True:
      next_task = self.task_queue.get()
      if next_task is None:
          #print 'Tasks complete on this thread'
          self.task_queue.task_done()
          break
      answer = next_task(connection=self.pyConn)
      self.task_queue.task_done()
      self.result_queue.put(answer)
    return


class Task(object):
  # Assign check and year when initialized
  def __init__(self, table, source_id, field):
    self.table = table
    self.source_id = source_id
    self.field = field

  # Acts as the controller for a given year
  def __call__(self, connection=None):
    def query_down(strictNameMatch, strictSpace, strictTime):
        match_type = field

        if not strictNameMatch:
            match_type += '_fname'

        if not strictSpace:
            match_type += '_fspace'

        if not strictTime:
            match_type += '_ftime'

        pyCursor.execute("""
          INSERT INTO maps.map_units (map_id, unit_id, basis_col)
            WITH a AS (
              SELECT m.map_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
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
          "table": AsIs(table),
          "source_id": source_id,
          "field": AsIs(field),
          "match_type": match_type
        })

        pyConn.commit()

        print "        - Done with " + match_type + " (up)"


    def query_up(strictNameMatch, strictSpace, strictTime):
        match_type = field

        if not strictNameMatch:
            match_type += '_fname'

        if not strictSpace:
            match_type += '_fspace'

        if not strictTime:
            match_type += '_ftime'

        pyCursor.execute("""
          INSERT INTO maps.map_units (map_id, unit_id, basis_col)
            WITH a AS (
              SELECT m.map_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
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
          "table": AsIs(table),
          "source_id": source_id,
          "field": AsIs(field),
          "match_type": match_type
        })

        pyConn.commit()

        print "        - Done with " + match_type + " (down)"


    def query(strictNameMatch, strictSpace, strictTime):
        match_type = field

        if not strictNameMatch:
            match_type += '_fname'

        if not strictSpace:
            match_type += '_fspace'

        if not strictTime:
            match_type += '_ftime'

        pyCursor.execute("""
            INSERT INTO maps.map_units (map_id, unit_id, basis_col)
            WITH a AS (
              SELECT m.map_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
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
          "table": AsIs(table),
          "source_id": source_id,
          "field": AsIs(field),
          "match_type": match_type
        })

        pyConn.commit()

        print "        - Done with " + match_type


    def match() :
        # strictName, strictSpace, strictTime, useNullSet

        # Strict name, strict space, strict time
        a = query(True, True, True)

        # Strict name, fuzzy space, strict time
        b = query(True, False, True)

        # Fuzzy name, strict space, strict time
        c = query(False, True, True)

        # Strict name, strict space, fuzzy time
        d = query(True, True, False)

        # Fuzzy name, fuzzy space, strict time
        e = query(False, False, True)

        # Strict name, fuzzy space, fuzzy time
        f = query(True, False, False)

        # Fuzzy name, strict space, fuzzy time
        g = query(False, True, False)

        # Fuzzy name, fuzzy space, fuzzy time
        h = query(False, False, False)


    def match_down() :
        # strictName, strictSpace, strictTime, useNullSet

        # Strict name, strict space, strict time
        a = query_down(True, True, True)

        # Strict name, fuzzy space, strict time
        b = query_down(True, False, True)

        # Fuzzy name, strict space, strict time
        c = query_down(False, True, True)

        # Strict name, strict space, fuzzy time
        d = query_down(True, True, False)

        # Fuzzy name, fuzzy space, strict time
        e = query_down(False, False, True)

        # Strict name, fuzzy space, fuzzy time
        f = query_down(True, False, False)

        # Fuzzy name, strict space, fuzzy time
        g = query_down(False, True, False)

        # Fuzzy name, fuzzy space, fuzzy time
        h = query_down(False, False, False)


    def match_up() :
        # strictName, strictSpace, strictTime

        # Strict name, strict space, strict time
        a = query_up(True, True, True)

        # Strict name, fuzzy space, strict time
        b = query_up(True, False, True)

        # Fuzzy name, strict space, strict time
        c = query_up(False, True, True)

        # Strict name, strict space, fuzzy time
        d = query_up(True, True, False)

        # Fuzzy name, fuzzy space, strict time
        e = query_up(False, False, True)

        # Strict name, fuzzy space, fuzzy time
        f = query_up(True, False, False)

        # Fuzzy name, strict space, fuzzy time
        g = query_up(False, True, False)

        # Fuzzy name, fuzzy space, fuzzy time
        h = query_up(False, False, False)


    pyConn = connection
    pyCursor = pyConn.cursor()

    # Time the process
    start_time = time.time()

    print "      * Working on ", self.field, " *"

    field = self.field
    table = self.table
    source_id = self.source_id

    match()
    match_down()
    match_up()


    elapsed = int(time.time() - start_time)
    print "        Done with ", self.field, " in ", elapsed / 60, " minutes and ", elapsed % 60, " seconds"
