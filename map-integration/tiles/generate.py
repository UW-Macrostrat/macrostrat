import sys
import psycopg2
from psycopg2.extensions import AsIs
import argparse
from subprocess import call

parser = argparse.ArgumentParser(
  description="(re)roll tiles for burwell",
  epilog="Example usage: python generate-tiles.py --all")

parser.add_argument("--source_id", dest="source_id",
  type=int, required=False,
  help="The ID of the desired source to generate")

parser.add_argument("--scale", dest="scale",
  type=str, required=False,
  help="The scale to regenerate. Can be 'small', 'medium', or 'large'.")

parser.add_argument("--all", dest="all",
  required=False, action="store_true",
  help="Regenerate all tiles")

arguments = parser.parse_args()


def return_help():
    parser.print_help()
    sys.exit(0)

if not arguments.all and not arguments.source_id and not arguments.scale:
    return_help()

# Connect to the database
try:
  conn = psycopg2.connect(dbname="burwell", user="john", host="localhost", port="5432")
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

# Create a cursor
cur = conn.cursor()

# Which zoom levels correspond to which map scales
scale_map = {
  "small": ["1", "2", "3", "4"],
  "medium": ["5", "6", "7", "8", "9"],
  "large": ["10", "11", "12"]
}

def find_groups(scale, source_id=None):
    params = {
      "scale": AsIs(scale)
    }

    pre = ""
    where = ""

    if source_id:
        pre = "WITH the_group AS (SELECT DISTINCT group_id FROM %(scale)s_map WHERE source_id = %(source_id)s LIMIT 1)"
        where = " WHERE group_id IN (SELECT * FROM the_group)"
        params["source_id"] = source_id

    cur.execute(pre + """
        SELECT group_id, ST_Extent(geom) AS extent
        FROM %(scale)s_map
        """ + where + """
        GROUP BY group_id
    """, params)
    groups = cur.fetchall()

    modified_groups = []
    for group in groups:
        # Extent comes back like BOX(min_lng, min_lat, max_lng, max_lat), but...
        # we need [min_lat, min_lng, max_lat, max_lng]
        clean_extent = group[1].replace("BOX(", "").replace(")", "").split(",")
        min_coords = clean_extent[0].split(" ")
        max_coords = clean_extent[1].split(" ")

        modified_groups.append({
            "group_id": group[0],
            "extent": [min_coords[1], min_coords[0], max_coords[1], max_coords[0]]
        })
    return modified_groups


def clear_cache(bbox, scale):
    cmd = ["python", "TileStache/scripts/tilestache-clean.py", "-b", bbox[0], bbox[1], bbox[2], bbox[3], "-c", "tilestache.cfg", "-l", "burwell"]
    cmd.extend(scale_map[scale])
    call(cmd)


def seed_cache(bbox, scale):
    cmd = ["python", "TileStache/scripts/tilestache-seed.py", "-b", bbox[0], bbox[1], bbox[2], bbox[3], "-c", "tilestache.cfg", "-l", "burwell"]
    cmd.extend(scale_map[scale])
    call(cmd)



if arguments.all:
    print "Do everything"

    # For each scale...
    for scale in ["small", "medium", "large"]:
        # Get a list of groups and their bboxes
        groups = find_groups(scale)
        # For each group...
        for group in groups:
            # Clear cache
            clear_cache(group["extent"], scale)
            # Reseed cache
            seed_cache(group["extent"], scale)



elif arguments.source_id:
    print "Do source_id"

    # Find the scale of this source_id
    cur.execute("SELECT scale from maps.sources WHERE source_id = %(source_id)s", {
        "source_id": arguments.source_id
    })
    scale = cur.fetchone()
    if scale is None:
        print "Invalid source_id given"
        sys.exit(1)

    # Find the group and corresponding bbox of this source_id
    group = find_groups(scale[0], arguments.source_id)

    print group
    group = group[0]

    # Clear the cache for this group
    clear_cache(group["extent"], scale[0])
    # Reseed cache
    seed_cache(group["extent"], scale[0])


elif arguments.scale:
    print "Do scale"

    # Get a list of groups and their bboxes for this scale
    groups = find_groups(arguments.scale)

    # For each group...
    for group in groups:
        # Clear cache
        clear_cache(group["extent"], arguments.scale)
        # Reseed cache
        seed_cache(group["extent"], arguments.scale)


else:
    print "Invalid params/combination of params"
    return_help()
