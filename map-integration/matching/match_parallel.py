import multiprocessing
from match_multiprocessor import *
import argparse
import psycopg2
from psycopg2.extensions import AsIs
import sys
import os
import datetime

sys.path = [os.path.join(os.path.dirname(__file__), os.pardir)] + sys.path
import credentials

cwd = os.path.dirname(os.path.realpath(__file__))

split_path = cwd.split("/")
split_path.pop()

sys.path.insert(0, "/".join(split_path) + "/setup")

import refresh

if __name__ == '__main__':

  connection = psycopg2.connect(dbname="burwell", user=credentials.pg_user, host=credentials.pg_host, port=credentials.pg_port)
  cursor = connection.cursor()

  parser = argparse.ArgumentParser(
    description="Match rocks to Macrostrat units",
    epilog="Example usage: python match.py --source_id 2")

  parser.add_argument("-s", "--source_id", dest="source_id",
    default="0", type=str, required=True,
    help="The ID of the desired source to match")

  parser.add_argument("-e", "--exclude", dest="exclude",
    default="", type=str, required=False,
    help="Field(s) that should be ommitted from the matching process. Ex: --exclude descrip,comments")

  arguments = parser.parse_args()

  # Validate params!
  # Valid source_id
  cursor.execute("SELECT source_id FROM maps.sources")
  sources = cursor.fetchall()
  source_ids = [source[0] for source in sources]
  if int(arguments.source_id) not in source_ids:
      print "Invalid source_id argument. Source ID ", arguments.source_id, " was not found in maps.sources"
      sys.exit(1)

  # Find scale table
  scale = ""
  for scale_table in ["tiny", "small", "medium", "large"]:
      cursor.execute("SELECT * FROM maps.%(table)s WHERE source_id = %(source_id)s LIMIT 1", {
        "table": AsIs(scale_table),
        "source_id": arguments.source_id
      })
      if cursor.fetchone() is not None:
        scale = scale_table
        break

  if len(scale) < 1:
      print "Provided source_id not found in maps.small, maps.medium, or maps.large. Please insert it and try again."
      sys.exit(1)


  print 'Starting at ', str(datetime.datetime.now())


  # Clean up
  cursor.execute("""
      DELETE FROM maps.map_units WHERE map_id IN (SELECT map_id FROM maps.%(table)s WHERE source_id = %(source_id)s) AND basis_col NOT LIKE 'manual%%'
  """, {
      "table": AsIs(scale),
      "source_id": arguments.source_id
  })

  cursor.execute("""
      DELETE FROM maps.map_strat_names WHERE map_id IN (SELECT map_id FROM maps.%(table)s WHERE source_id = %(source_id)s) AND basis_col NOT LIKE 'manual%%'
  """, {
      "table": AsIs(scale),
      "source_id": arguments.source_id
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

  ### Define our tasks ###

  # Fields in burwell to match on
  fields = ["strat_name", "name", "descrip", "comments"]

  # Remove the fields explicitly excluded
  exclude = arguments.exclude.split(",")
  for field in exclude:
    try :
      fields.remove(field)
    except:
      print 'Not excluding invalid field selection ', field

  # Insert a new task for each matching field into the queue
  for field in fields:
      tasks.put(Task(scale, arguments.source_id, field))

  for i in range(num_processors):
    tasks.put(None)

  tasks.join()

  scale = refresh.find_scale(cursor, arguments.source_id)
  if scale is not None:
      refresh.refresh(cursor, connection, scale, arguments.source_id)
      refresh.source_stats(cursor, connection, arguments.source_id)
      print "Refreshed lookup_" + scale + " for source_id ", arguments.source_id
