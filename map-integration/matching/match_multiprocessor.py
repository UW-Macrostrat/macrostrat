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

    def query(strictNameMatch, bufferedGeometry, useNullSet):
        match_type = field + ("" if strictNameMatch else "_fname") + ("_buffer" if bufferedGeometry else "")

        nullAddition = """
            AND (map_id NOT IN (
              SELECT a.map_id
              FROM maps.map_units a
              LEFT JOIN maps.%(table)s b
              ON a.map_id = b.map_id
              WHERE b.source_id = %(source_id)s
            ) OR map_id NOT IN (
              SELECT a.map_id
              FROM maps.map_strat_names a
              LEFT JOIN maps.%(table)s b
              ON a.map_id = b.map_id
              WHERE b.source_id = %(source_id)s
            ))
        """

        pyCursor.execute("""
            WITH rocks AS (SELECT map_id, replace(strat_name, '.', '') AS strat_name, replace(name, '.', '') AS name, descrip, comments, intervals_top.age_top, intervals_bottom.age_bottom, 25 as age_buffer, geom
                      FROM maps.%(table)s
                      JOIN macrostrat.intervals intervals_top on t_interval = intervals_top.id
                      JOIN macrostrat.intervals intervals_bottom on b_interval = intervals_bottom.id
                      WHERE source_id = %(source_id)s
                      """ + (nullAddition if useNullSet else "") + """
             ),
             macro AS (
                WITH first AS (
                    SELECT DISTINCT lsn.strat_name_id,
                      unnest(array(
                        SELECT not_null_names FROM (
                          SELECT unnest(
                            array[lsn.bed_name, lsn.mbr_name, lsn.fm_name, lsn.gp_name, lsn.sgp_name]
                          ) not_null_names
                        ) sub WHERE not_null_names IS NOT NULL
                      )) AS names,

                      unnest(array(
                        SELECT not_null_ids FROM (
                          SELECT unnest(
                            array[lsn.bed_id, lsn.mbr_id, lsn.fm_id, lsn.gp_id, lsn.sgp_id]
                          ) not_null_ids
                        ) sub WHERE not_null_ids != 0
                      )) AS strat_name_ids
                    FROM macrostrat.lookup_strat_names lsn
                    JOIN macrostrat.unit_strat_names usn ON usn.strat_name_id = lsn.strat_name_id
                    ORDER BY lsn.strat_name_id
                  )

                  SELECT units.id AS unit_id, """ + ("replace(lsn.rank_name, '.', '')" if strictNameMatch else "replace(lsn.name_no_lith, '.', '')") + """ AS strat_name, first.strat_name_ids AS strat_name_id, lui.lo_age AS age_top, lui.fo_age AS age_bottom, """ + ("st_buffer(st_envelope(poly_geom), 1.2) AS poly_geom " if bufferedGeometry else "poly_geom ") + """
                  FROM macrostrat.units
                  JOIN macrostrat.unit_strat_names usn ON units.id = usn.unit_id
                  JOIN first ON first.strat_name_id = usn.strat_name_id
                  JOIN macrostrat.units_sections us ON us.unit_id = units.id
                  JOIN macrostrat.cols ON cols.id = us.col_id
                  JOIN macrostrat.lookup_unit_intervals lui ON units.id = lui.unit_id
                  JOIN macrostrat.lookup_strat_names lsn ON first.strat_name_ids = lsn.strat_name_id
                  WHERE cols.status_code = 'active'
             )
            SELECT DISTINCT rocks.map_id, macro.unit_id, macro.strat_name_id FROM rocks, macro
            WHERE macro.strat_name != ''
                AND ST_Intersects(rocks.geom, macro.poly_geom)
                AND rocks.%(field)s ~* concat('\y', macro.strat_name, '\y')
                AND (((macro.age_top) <= (rocks.age_bottom + rocks.age_buffer))
                AND ((rocks.age_top - rocks.age_buffer) <= (macro.age_bottom)))
        """, {
          "table": AsIs(table),
          "source_id": source_id,
          "field": AsIs(field)
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
                "field": match_type
            })

            # Insert into maps.map_strat_names
            pyCursor.execute("""
                INSERT INTO maps.map_strat_names VALUES (%(map_id)s, %(strat_name_id)s, %(field)s)
            """, {
                "map_id": row[0],
                "strat_name_id": row[2],
                "field": match_type
            })

        pyConn.commit()

        print "        Done with " + match_type
        return len(results)


    pyConn = connection
    pyCursor = pyConn.cursor()

    # Time the process
    start_time = time.time()

    print "-------  Working on ", self.field, " -------"

    field = self.field
    table = self.table
    source_id = self.source_id

    # strictNameMatch, bufferedGeometry, useNullSet

    # Strict space, strict strat name
    a = query(True, False, False)

    # Strict space, fuzzy strat name
    b = query(False, False, True)

    # Buffered space, strict strat name
    c = query(True, True, True)

    # Buffered space, fuzz strat name
    d = query(False, True, True)


    elapsed = int(time.time() - start_time)
    print "Done with ", self.field, " - inserted ", (a + b + c + d), " records into maps.unit_strat_names and maps.units in ", elapsed / 60, " minutes and ", elapsed % 60, " seconds"
