import psycopg2
from psycopg2.extensions import AsIs
from subprocess import call
import json
import sys, os
import copy

# Connect to the database
try:
  conn = psycopg2.connect(dbname="burwell", user="john", host="localhost", port="5432")
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

cur = conn.cursor()


maps = ["small", "medium", "large"]


layer_template = {
    "geometry": "polygon",
    "extent": [
        -139.063199937376,
        -44.777735976,
        167.998035,
        60.0019261978321
    ],
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

# Get ready
with open("burwell.mml") as input:
    burwell = json.load(input)

if not os.path.exists('tmp'):
    os.makedirs('tmp')

for scale in maps:
    name = scale + "_map"

    cur.execute("SELECT ST_Extent(geom), ST_AsText(ST_Centroid(ST_Extent(geom))) FROM %(table)s", {"table": AsIs(name)})
    attrs = cur.fetchone()

    layer = copy.deepcopy(layer_template)
    extent = attrs[0].replace(" ", ",").replace("BOX(", "").replace(")", "")
    center = attrs[1].replace("POINT(", "").replace(")", "")

    layer["bounds"] = [float(coord) for coord in extent.split(",")]
    layer["center"] = [float(coord) for coord in center.split(" ")].append(3)
    layer["extent"] = [float(coord) for coord in extent.split(",")]
    layer["Datasource"]["extent"] = extent
    layer["Datasource"]["table"] = "(SELECT * FROM %s ) subset" % (name,)
    layer["id"] = name
    layer["name"] = name

    burwell["Layer"].append(layer)




with open("burwell_configured.mml", "wb") as output:
    json.dump(burwell, output, indent=2)

call(["node", "node_modules/kosmtik/index.js", "export", "burwell_configured.mml", "--format", "xml", "--output", "burwell_configured.xml", "--minZoom", "1", "max_zoom", "12"])
