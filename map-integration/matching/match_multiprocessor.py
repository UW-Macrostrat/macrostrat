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
    pyConn = connection
    pyCursor = pyConn.cursor()

    # Time the process
    start_time = time.time()

    print "-------  Working on ", self.field, " -------"

    pyCursor.execute("""
    WITH rocks AS (SELECT map_id, strat_name, name, descrip, comments, intervals_top.age_top, intervals_bottom.age_bottom, 25 as age_buffer, geom
              FROM maps.%(table)s
              JOIN macrostrat.intervals intervals_top on t_interval = intervals_top.id
              JOIN macrostrat.intervals intervals_bottom on b_interval = intervals_bottom.id
              WHERE source_id = %(source_id)s
     ),
     macro AS (SELECT us.unit_id AS unit_id, lsn.strat_name_id, lsn.strat_name, c.poly_geom, lui.lo_age as age_top, lui.fo_age as age_bottom
              FROM macrostrat.units_sections us
              JOIN macrostrat.lookup_unit_intervals lui ON us.unit_id = lui.unit_id
              JOIN macrostrat.unit_strat_names usn ON us.unit_id = usn.unit_id
              JOIN macrostrat.lookup_strat_names lsn ON usn.strat_name_id = lsn.strat_name_id
              JOIN macrostrat.cols c ON us.col_id = c.id
              WHERE c.status_code = 'active'
     )
    SELECT DISTINCT rocks.map_id, macro.unit_id, macro.strat_name_id FROM rocks, macro
    WHERE macro.strat_name != ''
        AND ST_Intersects(rocks.geom, macro.poly_geom)
        AND rocks.%(field)s ~* concat('\y', macro.strat_name, '\y')
        AND (((macro.age_top) <= (rocks.age_bottom + rocks.age_buffer))
        AND ((rocks.age_top - rocks.age_buffer) <= (macro.age_bottom)))

    """, {
      "table": AsIs(self.table),
      "source_id": self.source_id,
      "field": AsIs(self.field)
    })

    results = pyCursor.fetchall()

    for row in results:
        # 0 = map_id, 1 = unit_id, 2 = strat_name_id
        # Insert into maps.map_units
        pyCursor.execute("""
            INSERT INTO maps.map_units VALUES (%(map_id)s, %(unit_id)s, %(field)s)
        """, {
            "map_id": row[0],
            "unit_id": row[1],
            "field": self.field
        })

        # Insert into maps.map_strat_names
        pyCursor.execute("""
            INSERT INTO maps.map_strat_names VALUES (%(map_id)s, %(strat_name_id)s, %(field)s)
        """, {
            "map_id": row[0],
            "strat_name_id": row[2],
            "field": self.field
        })

    pyConn.commit()

    elapsed = int(time.time() - start_time)
    print "Done with ", self.field, " - inserted ", len(results), " records into maps.unit_strat_names and maps.units in ", elapsed / 60, " minutes and ", elapsed % 60, " seconds"
