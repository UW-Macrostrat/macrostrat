import multiprocessing
from match_multiprocessor import *
import argparse
import psycopg2
from psycopg2.extensions import AsIs
import sys
import os

sys.path = [os.path.join(os.path.dirname(__file__), os.pardir)] + sys.path
import credentials


if __name__ == '__main__':

  connection = psycopg2.connect(dbname="burwell", user=credentials.pg_user, host=credentials.pg_host, port=credentials.pg_port)
  cursor = connection.cursor()

  parser = argparse.ArgumentParser(
    description="Match rocks to Macrostrat units",
    epilog="Example usage: python match.py --source_id 2 --table medium")

  parser.add_argument("-s", "--source_id", dest="source_id",
    default="0", type=str, required=True,
    help="The ID of the desired source to match")

  parser.add_argument("-t", "--table", dest="table",
    default="small", type=str, required=True,
    help="The scale table to use. Can be 'small', 'medium', or 'large'.")

  arguments = parser.parse_args()

  # Validate params!
  if arguments.table not in ["small", "medium", "large"]:
      print "Invalid table argument"
      sys.exit(1)

  cursor.execute("SELECT source_id FROM maps.sources")
  sources = cursor.fetchall()
  source_ids = [source[0] for source in sources]
  if int(arguments.source_id) not in source_ids:
      print "Invalid source_id argument. Source ID ", arguments.source_id, " was not found in maps.sources"
      sys.exit(1)


  # Clean up
  cursor.execute("""
      DELETE FROM maps.map_units WHERE map_id IN (SELECT map_id FROM maps.%(table)s WHERE source_id = %(source_id)s)
  """, {
      "table": AsIs(arguments.table),
      "source_id": AsIs(arguments.source_id)
  })

  cursor.execute("""
      DELETE FROM maps.map_strat_names WHERE map_id IN (SELECT map_id FROM maps.%(table)s WHERE source_id = %(source_id)s)
  """, {
      "table": AsIs(arguments.table),
      "source_id": AsIs(arguments.source_id)
  })
  connection.commit()
  print "------- Done cleaning up -------"



  tasks = multiprocessing.JoinableQueue()
  results = multiprocessing.Queue()

  num_processors = 1
  if multiprocessing.cpu_count() < 4 :
      num_processors = multiprocessing.cpu_count()
  else :
      num_processors = 4

  processors = [Processor(tasks, results) for i in xrange(num_processors)]

  for each in processors:
    each.start()

  # Define our tasks
  tasks.put(Task(arguments.table, arguments.source_id, "strat_name" ))
  tasks.put(Task(arguments.table, arguments.source_id, "name" ))
  tasks.put(Task(arguments.table, arguments.source_id, "descrip" ))
  tasks.put(Task(arguments.table, arguments.source_id, "comments" ))


  for i in range(num_processors):
    tasks.put(None)
