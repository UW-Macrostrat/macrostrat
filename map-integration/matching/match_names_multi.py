# Adapted/borrowed from http://stackoverflow.com/a/7556042/1956065
import multiprocessing
import psycopg2
from psycopg2.extensions import AsIs
import time
import sys
import os
import yaml

with open(os.path.join(os.path.dirname(__file__), '../credentials.yml'), 'r') as f:
    credentials = yaml.load(f)

class Processor(multiprocessing.Process):

  def __init__(self, task_queue, result_queue):
    multiprocessing.Process.__init__(self)
    self.task_queue = task_queue
    self.result_queue = result_queue
    self.pyConn = psycopg2.connect(dbname=credentials["pg_db"], user=credentials["pg_user"], host=credentials["pg_host"], port=credentials["pg_port"])
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

    def query(strictNameMatch, strictSpace, strictTime, useNullSet):
        match_type = field

        if not strictNameMatch:
            match_type += '_fname'

        if not strictSpace:
            match_type += '_fspace'

        if not strictTime:
            match_type += '_ftime'

        pyCursor.execute("""
        INSERT INTO maps.map_strat_names
            SELECT unnest(rocks.map_ids), strat_name_id, %(match_type)s
            FROM macrostrat.strat_name_footprints snft
            JOIN (
              SELECT array_agg(map_id) AS map_ids, name, strat_name, age, lith, descrip, comments, t_interval, b_interval, ST_Envelope(ST_Collect(geom)) envelope
              FROM maps.%(table)s
              WHERE source_id = %(source_id)s
              GROUP BY name, strat_name, age, lith, descrip, comments, t_interval, b_interval
            ) rocks ON ST_Intersects(""" + ("rocks.envelope" if strictSpace else "ST_Buffer(rocks.envelope, 1.2)") + """, snft.geom)
            JOIN macrostrat.intervals intervals_top on rocks.t_interval = intervals_top.id
            JOIN macrostrat.intervals intervals_bottom on rocks.b_interval = intervals_bottom.id
            WHERE ((snft.best_t_age) < (intervals_bottom.age_bottom))
              AND ((snft.best_b_age) > (intervals_top.age_top))
              AND rocks.%(field)s ~* concat('\y', """ + ("replace(snft.rank_name, '.', '')" if strictNameMatch else "replace(snft.name_no_lith, '.', '')") + """, '\y')
            AND snft.strat_name_id IN (
              SELECT DISTINCT lsn4.strat_name_id
              FROM macrostrat.lookup_strat_names AS lsn4
              JOIN macrostrat.strat_name_footprints ON strat_name_footprints.strat_name_id = lsn4.strat_name_id
              CROSS JOIN (
                SELECT DISTINCT replace(%(field)s, '.', '') AS rock_match_field
                FROM maps.%(table)s
                WHERE source_id = %(source_id)s
              ) AS distinct_rocks
              WHERE distinct_rocks.rock_match_field ~* concat('\y', """ + ("replace(lsn4.rank_name, '.', '')" if strictNameMatch else "replace(lsn4.name_no_lith, '.', '')") + """, '\y')
              AND ST_Intersects(strat_name_footprints.geom, (
                SELECT """ + ("rgeom " if strictSpace else "ST_Buffer(rgeom, 1.2) ") + """
                FROM maps.sources
                WHERE source_id = %(source_id)s
              ))
            )
        """, {
          "table": AsIs(table),
          "source_id": source_id,
          "field": AsIs(field),
          "match_type": match_type
        })

        pyConn.commit()

        print "        - Done with " + match_type


    pyConn = connection
    pyCursor = pyConn.cursor()

    # Time the process
    start_time = time.time()

    print "      * Working on ", self.field, " *"

    field = self.field
    table = self.table
    source_id = self.source_id

    # strictNameMatch, strictSpace, strictTime, useNullSet

    # Strict name, strict space, strict time
    a = query(True, True, True, False)

    # Strict name, fuzzy space, strict time
    b = query(True, False, True, True)

    # Fuzzy name, strict space, strict time
    c = query(False, True, True, True)

    # Strict name, strict space, fuzzy time
    d = query(True, True, False, True)

    # Fuzzy name, fuzzy space, strict time
    e = query(False, False, True, True)

    # Strict name, fuzzy space, fuzzy time
    f = query(True, False, False, True)

    # Fuzzy name, strict space, fuzzy time
    g = query(False, True, False, True)

    # Fuzzy name, fuzzy space, fuzzy time
    h = query(False, False, False, True)


    elapsed = int(time.time() - start_time)
    print "        Done with ", self.field, " in ", elapsed / 60, " minutes and ", elapsed % 60, " seconds"
