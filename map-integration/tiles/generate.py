import sys, os
import psycopg2
from psycopg2.extensions import AsIs
import argparse
import copy
import json
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

def setup():
    print "--- Building styles.mss ---"
    # First, rebuild the file `styles.mss` in the event any colors were changed
    cur.execute("""
        SELECT DISTINCT interval_color AS color
        FROM macrostrat.intervals
        WHERE interval_color IS NOT NULL
            AND interval_color != ''
    """)
    colors = cur.fetchall()

    carto_css = """
    .burwell {
      polygon-opacity:1;
      polygon-fill: #000;
      line-color: #aaa;
      line-width: 0.0;
    }
    #small_map[zoom>5] {
      polygon-opacity: 0;
      line-opacity: 0;
    }
    #medium_map[zoom<=5]{
      polygon-opacity: 0;
      line-opacity: 0;
    }
    #medium_map[zoom>=10] {
      polygon-opacity: 0;
      line-opacity: 0;
    }
    #large_map[zoom<=9] {
      polygon-opacity: 0;
      line-opacity: 0;
    }

    .burwell[color="null"] {
       polygon-fill: #777777;
    }
    .burwell[color=null] {
       polygon-fill: #777777;
    }
    .burwell[color=""] {
       polygon-fill: #777777;
    }

    """

    # Build the stylesheet
    for color in colors :
      carto_css += '.burwell[color="' + color[0] + '"] {\n   polygon-fill: ' + color[0] + ';\n}\n'

    # Write it out
    with open("styles.mss", "w") as output:
        output.write(carto_css)

    print "--- Building burwell_configured.mml ---"

    # This is the template for each layer
    layer_template = {
        "geometry": "polygon",
        "extent": [],
        "Datasource": {
            "type": "postgis",
            "table": "",
            "key_field": "map_id",
            "geometry_field": "geom",
            "extent_cache": "auto",
            "extent": "",
            "host": "localhost",
            "port": "5432",
            "user": "john",
            "dbname": "burwell"
        },
        "id": "",
        "class": "burwell",
        "srs-name": "WGS84",
        "srs": "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
        "advanced": {},
        "name": ""
    }

    # Instantiate the project template that will hold each layer
    burwell = {
      "bounds": [-180, -90, 180, 90],
      "center": [0, 0, 1],
      "format": "png8",
      "interactivity": False,
      "minzoom": 0,
      "maxzoom": 12,
      "srs": "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over",
      "Stylesheet": [
        "styles.mss"
      ],
      "Layer": [],
      "scale": 1,
      "metatile": 2,
      "name": "burwell",
      "description": "burwell",
      "attribution": "Data providers, UW-Macrostrat, John J Czaplewski <jczaplew@gmail.com>"
    }


    # For each scale...
    for scale in ["small", "medium", "large"]:
        name = scale + "_map"

        # ...find the extent and the centroid
        cur.execute("SELECT ST_Extent(geom), ST_AsText(ST_Centroid(ST_Extent(geom))) FROM %(table)s", {"table": AsIs(name)})
        attrs = cur.fetchone()

        # ...create a new layer template
        layer = copy.deepcopy(layer_template)

        # ...clean up the extent and centroid from the above query
        extent = attrs[0].replace(" ", ",").replace("BOX(", "").replace(")", "")
        center = attrs[1].replace("POINT(", "").replace(")", "")

        # ...fill in the template
        layer["bounds"] = [float(coord) for coord in extent.split(",")]
        layer["center"] = [float(coord) for coord in center.split(" ")].append(3)
        layer["extent"] = [float(coord) for coord in extent.split(",")]
        layer["Datasource"]["extent"] = extent
        layer["Datasource"]["table"] = "(SELECT * FROM %s ) subset" % (name,)
        layer["id"] = name
        layer["name"] = name

        # ...and append the layer to the project
        burwell["Layer"].append(layer)

    # Dump the resultant configuration file to a new project file
    with open("burwell_configured.mml", "wb") as output:
        json.dump(burwell, output, indent=2)

    print "--- Building burwell_configured.xml with kosmtik---"

    # Use kosmtik top convert the project file to a Mapnik XML file that can be read by TileStache
    call(["node", "node_modules/kosmtik/index.js", "export", "burwell_configured.mml", "--format", "xml", "--output", "burwell_configured.xml", "--minZoom", "1", "--max_zoom", "12"])

    call(["cp", "burwell_configured.xml", "TileStache/burwell_configured.xml"])


def find_groups(scale, source_id=None):
    params = {
      "scale": AsIs(scale)
    }

    pre = ""
    where = ""

    # If a source_id is supplied, find the group_id that it belongs to
    if source_id:
        pre = "WITH the_group AS (SELECT DISTINCT group_id FROM %(scale)s_map WHERE source_id = %(source_id)s LIMIT 1)"
        where = " WHERE group_id IN (SELECT * FROM the_group)"
        params["source_id"] = source_id

    # Get the extent of the target group(s)
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

    # Return an array of objects, where each object has group_id and a corresponding extent
    return modified_groups


# Wrapper for tilestache-clean.py
def clear_cache(bbox, scale):
    cmd = ["python", "TileStache/scripts/tilestache-clean.py", "-b", bbox[0], bbox[1], bbox[2], bbox[3], "-c", "tilestache.cfg", "-l", "burwell"]
    cmd.extend(scale_map[scale])
    call(cmd)

# Wrapper for tilestache-seed.py
def seed_cache(bbox, scale):
    cmd = ["python", "TileStache/scripts/tilestache-seed.py", "-b", bbox[0], bbox[1], bbox[2], bbox[3], "-c", "tilestache.cfg", "-l", "burwell"]
    cmd.extend(scale_map[scale])
    call(cmd)


# First update the cartocss and project file
setup()

# Process the commandline args
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