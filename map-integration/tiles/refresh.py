import psycopg2
from psycopg2.extensions import AsIs
import sys, os
import argparse

parser = argparse.ArgumentParser(
  description="Refresh materialized views",
  epilog="Example usage: python refresh.py medium")

parser.add_argument(dest="refresh",
  type=str, nargs=1,
  help="The scale to refresh. If new sources were added, make sure to refresh. Can be 'small', 'medium', 'large', or 'all'. Default will not refresh materialized views.")

arguments = parser.parse_args()

# Connect to the database
try:
  conn = psycopg2.connect(dbname="burwell", user="john", host="localhost", port="5432")
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

cur = conn.cursor()

if len(arguments.refresh) == 1:
    print "--- Refreshing views ---"
    if arguments.refresh[0] == "all":
        print "---      small       ---"
        cur.execute("REFRESH MATERIALIZED VIEW small_map")
        print "---      medium      ---"
        cur.execute("REFRESH MATERIALIZED VIEW medium_map")
        print "---      large       ---"
        cur.execute("REFRESH MATERIALIZED VIEW large_map")
        conn.commit()
    elif arguments.refresh[0] == "small":
        print "---      small       ---"
        cur.execute("REFRESH MATERIALIZED VIEW small_map")
        conn.commit()
    elif arguments.refresh[0] == "medium":
        print "---      medium       ---"
        cur.execute("REFRESH MATERIALIZED VIEW medium_map")
        conn.commit()
    elif arguments.refresh[0] == "large":
        print "---      large       ---"
        cur.execute("REFRESH MATERIALIZED VIEW large_map")
        conn.commit()
