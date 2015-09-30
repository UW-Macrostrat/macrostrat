import sys, os
import psycopg2
from psycopg2.extensions import AsIs
import copy
import json
from subprocess import call, check_call, CalledProcessError
import subprocess


# Burwell_tiny = tiny [0, 1, 2, 3, 4]
# Burwell_small = small, medium, large [5, 6]
# Burwell_medium = medium, small, large [7, 8, 9, 10, 11]
# Burwell_large = large, medium, small [12, 13]

# For each, build a new project file, using the same stylesheet


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
        "dbname": "burwell",
        "srid": "4326"
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


def clean_up():
    try:
        check_call("rm burwell_large.mml && rm burwell_medium.mml && rm burwell_small.mml && rm burwell_tiny.mml && rm -rf tmp", shell=True)
    except CalledProcessError:
        print "Error cleaning up files"
        sys.exit()


# First update the cartocss and project file
setup()
clean_up()
