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

print "--- Refreshing views ---"
print "---      small       ---"
#cur.execute("REFRESH MATERIALIZED VIEW small_map")
print "---      medium      ---"
#cur.execute("REFRESH MATERIALIZED VIEW medium_map")
print "---      large       ---"
#cur.execute("REFRESH MATERIALIZED VIEW large_map")
#conn.commit()

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
#medium_map[zoom>=11] {
  polygon-opacity: 0;
  line-opacity: 0;
}
#large_map[zoom<=10] {
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

# Open the project template that will hold each layer
with open("burwell.mml") as input:
    burwell = json.load(input)

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

print "--- Building burwell_configured.xml ---"

# Use kosmtik top conver the project file to a Mapnik XML file that can be read by TileStache
call(["node", "node_modules/kosmtik/index.js", "export", "burwell_configured.mml", "--format", "xml", "--output", "burwell_configured.xml", "--minZoom", "1", "--max_zoom", "12"])
