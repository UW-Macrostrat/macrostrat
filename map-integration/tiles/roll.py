import psycopg2
from psycopg2.extensions import AsIs
from subprocess import call
import json
#from collections import OrderedDict
import sys, os
import sqlite3

def new_mbtiles(filename):
    temp_conn = sqlite3.connect(table + ".mbtiles")
    temp_cursor = temp_conn.cursor()
    temp_cursor.execute("PRAGMA cache_size = 40000")
    temp_cursor.execute("PRAGMA temp_store = memory")

    temp_cursor.execute("""
        CREATE TABLE tiles (
            zoom_level integer,
            tile_column integer,
            tile_row integer,
            tile_data blob
        );
    """)
    update combined.tiles set tile_data = (select gmus.tiles.tile_data from gmus.tiles where length(combined.tiles.tile_data) < length(gmus.tiles.tile_data) AND combined.tiles.zoom_level = gmus.tiles.zoom_level AND combined.tiles.tile_column = gmus.tiles.tile_column AND combined.tiles.tile_row = gmus.tiles.tile_row)

    temp_cursor.execute("CREATE TABLE metadata (name text, value text)")
    temp_cursor.execute("CREATE UNIQUE INDEX name on metadata (name)")
    temp_cursor.execute("CREATE UNIQUE INDEX tile_index on tiles (zoom_level, tile_column, tile_row)")
    temp_conn.commit()
    temp_conn.close()


# Connect to the database
try:
  conn = psycopg2.connect(dbname="burwell", user="john", host="localhost", port="5432")
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

cur = conn.cursor()

table = "medium_map"
sqlite3_connection = sqlite3.connect(":memory")
sqlite3_cursor = sqlite3_connection.cursor()
sqlite3_cursor.execute("PRAGMA cache_size = 40000")
sqlite3_cursor.execute("PRAGMA page_size = 80000")
#sqlite3_cursor.execute("PRAGMA synchronous = OFF")
sqlite3_cursor.execute("PRAGMA temp_store = memory")
sqlite3_cursor.execute("PRAGMA journal_mode = DELETE")
sqlite3_cursor.execute("PRAGMA locking_mode = EXCLUSIVE")
sqlite3_connection.commit()
new_mbtiles(table)

# Get ready

with open("template.mml") as input:
    template = json.load(input)

if not os.path.exists('tmp'):
    os.makedirs('tmp')

cur.execute("SELECT DISTINCT group_id FROM %(table)s", {"table": AsIs(table)})
groups = [group[0] for group in cur.fetchall()]

sqlite3_cursor.execute("attach database ? AS combined", (table + ".mbtiles", ))
sqlite3_connection.commit()

for group in groups :
    cur.execute("SELECT ST_Extent(geom), ST_AsText(ST_Centroid(ST_Extent(geom))) FROM %(table)s WHERE group_id = %(group_id)s", {"table": AsIs(table), "group_id": group})
    attrs = cur.fetchone()
    source_project = template.copy()

    extent = attrs[0].replace(" ", ",").replace("BOX(", "").replace(")", "")
    center = attrs[1].replace("POINT(", "").replace(")", "")
    name = table + str(group)

    source_project["bounds"] = [float(coord) for coord in extent.split(",")]
    source_project["center"] = [float(coord) for coord in center.split(" ")].append(3)
    source_project["Layer"][0]["extent"] = [float(coord) for coord in extent.split(",")]
    source_project["Layer"][0]["Datasource"]["extent"] = extent
    source_project["Layer"][0]["Datasource"]["table"] = "(SELECT * FROM %s WHERE group_id = %s) subset" % (table, group, )
    source_project["Layer"][0]["id"] = name
    source_project["Layer"][0]["name"] = name
    source_project["name"] = name

    file_name = "tmp/" + name + ".mml"
    with open(file_name, "wb") as output:
        json.dump(source_project, output, indent=2)

    call(["node", "node_modules/kosmtik/index.js", "export", file_name, "--format", "tiles", "--output", ("tmp/" + name + "_tiles"), "--minZoom", "1", "--maxZoom", "4"])
    call(["mb-util", ("tmp/" + name + "_tiles"), ("tmp/" + name + ".mbtiles")])
    sqlite3_cursor.execute("ATTACH DATABASE ? AS " + name, ("tmp/" + name + ".mbtiles", ))
    sqlite3_cursor.execute("REPLACE INTO combined.tiles SELECT * FROM " + name + ".tiles")

sqlite3_connection.commit()
