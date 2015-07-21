import psycopg2
import json
from collections import OrderedDict
import sys, os


# Connect to the database
try:
  conn = psycopg2.connect(dbname="burwell", user="john", host="localhost", port="5432")
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

cur = conn.cursor()

cur.execute("select distinct interval_color as color FROM macrostrat.intervals WHERE interval_color IS NOT NULL AND interval_color != ''")
colors = cur.fetchall()

carto_css = """
.burwell {
  polygon-opacity:1;
  polygon-fill: #000;
  line-color: #aaa;
  line-width: 0.0;
}
#small_map[zoom>6] {
  polygon-opacity: 0;
  line-opacity: 0;
}
#medium_map[zoom<=6]{
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


for color in colors :
  carto_css += '.burwell[color="' + color[0] + '"] {\n   polygon-fill: ' + color[0] + ';\n}\n'

with open("styles.mss", "w") as output:
    output.write(carto_css)
