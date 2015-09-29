import sys, os
import psycopg2
from psycopg2.extensions import AsIs
import argparse
import copy
import json
import multiprocessing
from subprocess import call, check_call, CalledProcessError
import subprocess

parser = argparse.ArgumentParser(
  description="(re)roll tiles for burwell",
  epilog="Example usage: python generate-tiles.py --all")

parser.add_argument("--source_id", dest="source_id",
  type=int, required=False,
  help="The ID of the desired source to generate")

parser.add_argument("--scale", dest="scale",
  type=str, required=False,
  help="The scale to regenerate. Can be 'tiny', 'small', 'medium', or 'large'.")

parser.add_argument("--all", dest="all",
  required=False, action="store_true",
  help="Regenerate all tiles")

arguments = parser.parse_args()

cpus = multiprocessing.cpu_count() - 2

# Burwell_tiny = tiny [0, 1, 2, 3, 4]
# Burwell_small = small, medium, large [5, 6]
# Burwell_medium = medium, small, large [7, 8, 9, 10, 11]
# Burwell_large = large, medium, small [12, 13]

# For each, build a new project file, using the same stylesheet

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
  "tiny": ["0", "1", "2", "3", "4"],
  "small": ["5", "6"],
  "medium": ["7", "8", "9", "10", "11"],
  "large": ["12", "13"]
}

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
    "name": "",
    "minZoom": "",
    "maxZoom": ""
}

# Instantiate the project template that will hold each layer
burwell = {
  "bounds": [-89,-179,89,179],
  "center": [0, 0, 1],
  "format": "png8",
  "interactivity": False,
  "minzoom": 0,
  "maxzoom": 13,
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

def create_layer(scale) :
    name = "lookup_" + scale

    # ...find the extent and the centroid
    cur.execute("SELECT ST_Extent(s.geom), ST_AsText(ST_Centroid(ST_Extent(geom))) FROM %(table)s x JOIN maps.%(scale)s s ON s.map_id = x.map_id", {"table": AsIs(name), "scale": AsIs(scale)})
    attrs = cur.fetchone()

    # ...create a new layer template
    layer = copy.deepcopy(layer_template)

    # ...clean up the extent and centroid from the above query
    extent = attrs[0].replace(" ", ",").replace("BOX(", "").replace(")", "")
    center = attrs[1].replace("POINT(", "").replace(")", "")

    # ...fill in the template
    layer["bounds"] = [float(coord) for coord in extent.split(",")]
    layer["center"] = [float(coord) for coord in center.split(" ")].append(3)
    layer["extent"] = [-179, -89, 179, 89]
    layer["Datasource"]["extent"] = "-179,-89,179,89"
    layer["Datasource"]["table"] = "(SELECT x.map_id, x.group_id, x.color, geom FROM %s x JOIN maps.%s s ON s.map_id = x.map_id) subset" % (name, scale)
    layer["id"] = "burwell_" + scale
    layer["name"] = "burwell_" + scale
    layer["minZoom"] = min(scale_map[scale])
    layer["maxZoom"] = max(scale_map[scale])

    return layer


def clean_up_tmp():
    try:
        check_call("rm -rf tmp", shell=True)
    except CalledProcessError:
        print "Error deleting folder tmp"
        sys.exit()

def setup():
    clean_up_tmp()

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

    print "--- Building project files ---"


    for scale in ["tiny", "small", "medium", "large"]:
        if scale == "tiny":
            project = copy.deepcopy(burwell)
            project["minzoom"] = min(scale_map[scale])
            project["maxzoom"] = max(scale_map[scale])
            layer = create_layer("tiny")
            project["Layer"].append(layer)
            with open("burwell_tiny.mml", "wb") as output:
                json.dump(project, output, indent=2)

        elif scale == "small":
            project = copy.deepcopy(burwell)
            project["minzoom"] = min(scale_map[scale])
            project["maxzoom"] = max(scale_map[scale])
            for each in ["tiny", "large", "medium", "small"]:
                layer = create_layer(each)
                project["Layer"].append(layer)
            with open("burwell_small.mml", "wb") as output:
                json.dump(project, output, indent=2)

        elif scale == "medium":
            project = copy.deepcopy(burwell)
            project["minzoom"] = min(scale_map[scale])
            project["maxzoom"] = max(scale_map[scale])
            for each in ["large", "small", "medium"]:
                layer = create_layer(each)
                project["Layer"].append(layer)
            with open("burwell_medium.mml", "wb") as output:
                json.dump(project, output, indent=2)

        elif scale == "large":
            project = copy.deepcopy(burwell)
            project["minzoom"] = min(scale_map[scale])
            project["maxzoom"] = max(scale_map[scale])
            for each in ["medium", "large"]:
                layer = create_layer(each)
                project["Layer"].append(layer)
            with open("burwell_large.mml", "wb") as output:
                json.dump(project, output, indent=2)

        else:
            print "WTF?"


    # Build mapnik files
    print "--- Building Mapnik config files with kosmtik ---"

    for scale in ["tiny", "small", "medium", "large"]:
        # Use kosmtik top convert the project file to a Mapnik XML file that can be read by TileStache
        call(["node", "node_modules/kosmtik/index.js", "export", "burwell_" + scale + ".mml", "--format", "xml", "--output", "burwell_" + scale + ".xml", "--minZoom", min(scale_map[scale]), "--max_zoom", max(scale_map[scale])])

        #call(["cp", "burwell_" + scale + ".xml", "TileStache/burwell_" + scale + ".xml"])


def clean_up():
    try:
        check_call("rm burwell_large.* && rm burwell_medium.* && rm burwell_small.* && rm burwell_tiny.* && rm -rf tmp", shell=True)
    except CalledProcessError:
        print "Error cleaning up files"
        sys.exit()


def find_groups(scale, source_id=None):
    params = {
      "scale": AsIs(scale)
    }

    pre = ""
    where = ""

    # If a source_id is supplied, find the group_id that it belongs to
    if source_id:
        pre = "WITH the_group AS (SELECT DISTINCT group_id FROM lookup_%(scale)s x JOIN maps.%(scale)s s ON s.map_id = x.map_id WHERE s.source_id = %(source_id)s LIMIT 1)"
        where = " WHERE group_id IN (SELECT * FROM the_group)"
        params["source_id"] = source_id

    # Get the extent of the target group(s)
    cur.execute(pre + """
        SELECT group_id, ST_Extent(geom) AS extent
        FROM lookup_%(scale)s x
        JOIN maps.%(scale)s s ON s.map_id = x.map_id
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
'''
def clear_cache(bbox, scale):
    print "--- Cleaning cache ---"
    cmd = ["python", "TileStache/scripts/tilestache-clean.py", "-q", "-b", bbox[0], bbox[1], bbox[2], bbox[3], "-c", "tilestache.cfg", "-l", ("lookup_" + scale)]
    cmd.extend(scale_map[scale])
    call(cmd)
'''

# Wrapper for tilestache-seed.py
def seed_cache(bbox, scale):
    check_call("rm -rf tmp/*", shell=True)

    cmd = "python TileStache/scripts/tilestache-list.py -b " + " ".join(bbox) + " " +  " ".join(scale_map[scale]) + " | split -l 2500 - tmp/list- && ls -1 tmp/list-* | xargs -n1 -P" + str(cpus) + " TileStache/scripts/tilestache-seed.py -q -c tilestache.cfg -l burwell_" + scale + " --tile-list"

    #print cmd
    try:
        check_call(cmd, shell=True)
    except CalledProcessError:
        print "Error seeding cache at scale", scale
        sys.exit()


# First update the cartocss and project file
setup()

# Process the commandline args
if arguments.all:
    print "Do everything"

    # For each scale...
    for scale in ["tiny", "small", "medium", "large"]:
        # Get a list of groups and their bboxes
        #groups = find_groups(scale)
        print "--- Seeding cache for " + scale + " ---"

        seed_cache([-89, -189, 89, 189],scale)
        # For each group...
        #for idx, group in enumerate(groups):
        #    print "--- ", (idx + 1), " of ", len(groups), " ---"
            # Clear cache
            #clear_cache(group["extent"], scale)
            # Reseed cache
        #    seed_cache(group["extent"], scale)

        try:
            check_call("cp -R TileStache/tiles/burwell_" + scale + "/* TileStache/tiles/burwell", shell=True)
        except CalledProcessError:
            print "Error moving tiles to burwell directory @ ", scale
            sys.exit()

    clean_up()



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
