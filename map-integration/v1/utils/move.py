import argparse
import sys, os
import psycopg2
from psycopg2.extensions import AsIs
import yaml

with open(os.path.join(os.path.dirname(__file__), '../credentials.yml'), 'r') as f:
    credentials = yaml.load(f)

parser = argparse.ArgumentParser(
    description="Move a source from one scale to another",
    epilog="Example usage: python move.py --source_id 6 --current_scale small --dest_scale large")

parser.add_argument("-s", "--source_id", dest="source_id",
   default="0", type=str, required=True,
   help="The ID of the desired source to move")

parser.add_argument("-c", "--current_scale", dest="c_scale",
   default="0", type=str, required=True,
   help="The current scale")

parser.add_argument("-d", "--dest_scale", dest="d_scale",
   default="0", type=str, required=True,
   help="The destination scale")

arguments = parser.parse_args()

# Connect to the database
try:
  conn = psycopg2.connect(dbname=credentials["pg_db"], user=credentials["pg_user"], host=credentials["pg_host"], port=credentials["pg_port"])
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

# Create a cursor
cur = conn.cursor()


# Move from lookup_scale
cur.execute("""
    WITH to_move AS (
        DELETE FROM lookup_%(c_scale)s a
        USING maps.%(c_scale)s b
        WHERE a.map_id = b.map_id
        AND b.source_id = %(source_id)s
        RETURNING a.*
    )
    INSERT INTO lookup_%(d_scale)s
    SELECT * FROM to_move
""", {
    "c_scale": AsIs(arguments.c_scale),
    "source_id": arguments.source_id,
    "d_scale": AsIs(arguments.d_scale)
})
conn.commit()

# Move from primary table
cur.execute("""
    WITH to_move AS (
        DELETE FROM maps.%(c_scale)s a
        WHERE source_id = %(source_id)s
        RETURNING a.*
    )
    INSERT INTO maps.%(d_scale)s
    SELECT * FROM to_move
""", {
    "c_scale": AsIs(arguments.c_scale),
    "source_id": arguments.source_id,
    "d_scale": AsIs(arguments.d_scale)
})
conn.commit()

# Update meta table
cur.execute("""
    UPDATE maps.sources
    SET scale = %(d_scale)s
    WHERE source_id = %(source_id)s
""", {
    "d_scale": arguments.d_scale,
    "source_id": arguments.source_id
})
conn.commit()

print "Moved ", arguments.source_id, " from ", arguments.c_scale, " to ", arguments.d_scale
