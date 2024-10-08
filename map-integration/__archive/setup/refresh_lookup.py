import argparse
import os
import sys
import time

import psycopg2
import psycopg2.extras
import yaml
from psycopg2.extensions import AsIs

with open(os.path.join(os.path.dirname(__file__), '../credentials.yml'), 'r') as f:
    credentials = yaml.load(f)

import refresh

parser = argparse.ArgumentParser(
  description="Refresh lookup tables",
  epilog="Example usage: python refresh_lookup.py medium")

parser.add_argument(dest="refresh",
  type=str, nargs=1,
  help="A valid source_id or scale name to refresh. If new sources were added or matches were made, make sure to refresh. Can be any valid source_id, scale name, or 'all'. Default will not refresh anything.")

arguments = parser.parse_args()

# Connect to the database
try:
  connection = psycopg2.connect(dbname=credentials['pg_db'], user=credentials['pg_user'], host=credentials['pg_host'], port=credentials['pg_port'])
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

cursor = connection.cursor()

valid_scales = ["tiny", "small", "medium", "large"]


if len(arguments.refresh) == 1:
    # Refresh all scales
    if arguments.refresh[0] == "all":
        for scale in valid_scales:
            refresh.refresh_scale(cursor, connection, scale)

    # If a source_id was passed
    elif arguments.refresh[0].isdigit() :
        scale = refresh.find_scale(cursor, arguments.refresh[0])
        if scale and scale[0] is not None:
            refresh.refresh(cursor, connection, scale[0], arguments.refresh[0])
            print "Refreshed lookup_" + scale[0] + " for source_id ", arguments.refresh[0]

        else:
            print "This source_id was not found or is invalid"

    # If a scale was passed
    elif arguments.refresh[0] in valid_scales:
        refresh.refresh_scale(cursor, connection, arguments.refresh[0])

    # ?
    else:
        print "Invalid source_id given"
