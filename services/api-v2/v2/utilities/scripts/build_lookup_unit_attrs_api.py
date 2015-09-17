import MySQLdb
import MySQLdb.cursors
from warnings import filterwarnings
import sys
from collections import defaultdict
import json
import decimal
from credentials import *

# Connect to Macrostrat
try:
  connection = MySQLdb.connect(host=mysql_host, user=mysql_user, passwd=mysql_passwd, db=mysql_db, unix_socket=mysql_unix_socket, cursorclass=MySQLdb.cursors.DictCursor)
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

# Cursor for MySQL
cursor = connection.cursor()

# Ignore warnings
filterwarnings('ignore', category = MySQLdb.Warning)

def check_for_decimals(obj):
  if isinstance(obj, decimal.Decimal):
    return float(obj)
  raise TypeError


# Do this if running for the first time!
'''
DROP TABLE IF EXISTS lookup_unit_attrs_api;
DROP TABLE IF EXISTS lookup_unit_attrs_api_new;

CREATE TABLE lookup_unit_attrs_api (
  unit_id mediumint(8),
  lith blob,
  environ blob,
  econ blob,
  measure_short blob,
  measure_long blob
) ENGINE=MyISam ;
CREATE INDEX unit_id_idx ON lookup_unit_attrs_api (unit_id);

CREATE TABLE lookup_unit_attrs_api_new LIKE lookup_unit_attrs_api;
'''

# Create room for the new data
cursor.execute("TRUNCATE TABLE lookup_unit_attrs_api_new")

### First handle lithologies ###
cursor.execute("""
  SELECT unit_id, lith_id, lith, lith_type, lith_class, comp_prop, GROUP_CONCAT(lith_atts.lith_att SEPARATOR '|') AS lith_atts
  FROM unit_liths
  LEFT JOIN liths ON lith_id = liths.id
  LEFT JOIN unit_liths_atts ON unit_liths.id = unit_liths_atts.unit_lith_id
  LEFT JOIN lith_atts ON unit_liths_atts.lith_att_id = lith_atts.id
  GROUP BY unit_liths.id
  ORDER BY unit_id ASC
""")

units = cursor.fetchall()

# Group lithologies by unit_id
grouped_units = defaultdict(list)
for unit in units:
  atts = []
  if unit["lith_atts"] is not None:
    atts= unit["lith_atts"].split("|")

  grouped_units[unit["unit_id"]].append({
    "lith_id": unit["lith_id"],
    "atts": atts,
    "name": unit["lith"],
    "type": unit["lith_type"],
    "class": unit["lith_class"],
    "prop": unit["comp_prop"]
  })

# Update the lookup table with the jsonified structure
for unit in grouped_units:
  cursor.execute("""
    INSERT INTO lookup_unit_attrs_api_new (unit_id, lith) VALUES (%s, %s)
  """, [unit, json.dumps(grouped_units[unit], default=check_for_decimals)])


### Next handle environments ###
cursor.execute("""
  SELECT unit_id, environ_id, environ, environ_type, environ_class
  FROM unit_environs
  LEFT JOIN environs ON environ_id = environs.id
  ORDER BY unit_id ASC
""")

units = cursor.fetchall()

grouped_units = defaultdict(list)
for unit in units:
  grouped_units[unit["unit_id"]].append({
    "environ_id": unit["environ_id"],
    "name": unit["environ"],
    "type": unit["environ_type"],
    "class": unit["environ_class"],
  })

for unit in grouped_units:
  cursor.execute("""
    UPDATE lookup_unit_attrs_api_new SET environ = %s WHERE unit_id = %s
  """, [json.dumps(grouped_units[unit], default=check_for_decimals), unit])


### Next handle econs ###
cursor.execute("""
  SELECT unit_id, econ_id, econ, econ_type, econ_class
  FROM unit_econs
  LEFT JOIN econs ON econ_id = econs.id
  ORDER BY unit_id ASC
""")

units = cursor.fetchall()

grouped_units = defaultdict(list)
for unit in units:
  grouped_units[unit["unit_id"]].append({
    "econ_id": unit["econ_id"],
    "name": unit["econ"],
    "type": unit["econ_type"],
    "class": unit["econ_class"]
  })

for unit in grouped_units:
  cursor.execute("""
    UPDATE lookup_unit_attrs_api_new SET econ = %s WHERE unit_id = %s
  """, [json.dumps(grouped_units[unit], default=check_for_decimals), unit])

cursor.execute("""
  UPDATE lookup_unit_attrs_api_new SET econ = '[]' WHERE econ IS NULL
""")



### Next handle measurements short ###
cursor.execute("""
  SELECT DISTINCT
  measurement_class,
  measurement_type,
  unit_id
  FROM measurements JOIN measures ON measures.measurement_id = measurements.id
  JOIN measuremeta ON measures.measuremeta_id = measuremeta.id
  JOIN unit_measures ON measuremeta.id = unit_measures.measuremeta_id
""")

measurements = cursor.fetchall()

grouped_measurements = defaultdict(list)
for measurement in measurements:
  grouped_measurements[measurement["unit_id"]].append({
    "measure_class": measurement["measurement_class"],
    "measure_type": measurement["measurement_type"]
  })

for measurement in grouped_measurements:
  cursor.execute("""
    UPDATE lookup_unit_attrs_api_new SET measure_short = %s WHERE unit_id = %s
  """, [json.dumps(grouped_measurements[measurement], default=check_for_decimals), measurement])

cursor.execute("""
  UPDATE lookup_unit_attrs_api_new SET measure_short = '[]' WHERE measure_short IS NULL
""")



### Next handle measurements_long ####
cursor.execute("""
  SELECT measurements.id AS measure_id,
  measurement_class AS measure_class,
  measurement_type AS measure_type,
  measurement AS measure,
  round(avg(measure_value),5) AS mean,
  round(stddev(measure_value),5) AS stddev,
  count(unit_measures.id) AS n,
  units,
  unit_id
  FROM measures JOIN measurements ON measures.measurement_id = measurements.id
  JOIN measuremeta ON measures.measuremeta_id = measuremeta.id
  JOIN unit_measures ON measuremeta.id = unit_measures.measuremeta_id
  GROUP BY unit_id,measurements.id
""")

measurements = cursor.fetchall()

grouped_measurements = defaultdict(list)
for measurement in measurements:
  grouped_measurements[measurement["unit_id"]].append({
      "measure_id": measurement["measure_id"],
      "measure": measurement["measure"],
      "mean": measurement["mean"],
      "stddev": measurement["stddev"],
      "n": measurement["n"],
      "unit": measurement["units"]
    })

for measurement in grouped_measurements:
  cursor.execute("""
    UPDATE lookup_unit_attrs_api_new SET measure_long = %s WHERE unit_id = %s
  """, [json.dumps(grouped_measurements[measurement], default=check_for_decimals), measurement])

cursor.execute("""
  UPDATE lookup_unit_attrs_api_new SET measure_long = '[]' WHERE measure_long IS NULL
""")


### FINISH HIM ###
cursor.execute("TRUNCATE TABLE lookup_unit_attrs_api")
cursor.execute("INSERT INTO lookup_unit_attrs_api SELECT * FROM lookup_unit_attrs_api_new")

print "Done building lookup_unit_attrs_api"
