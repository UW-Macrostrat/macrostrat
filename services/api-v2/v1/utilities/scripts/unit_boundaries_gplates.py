import MySQLdb
import MySQLdb.cursors
import os
import sys
import json
import decimal
import urllib2
from credentials import *

# Connect to MySQL
my_conn = MySQLdb.connect(host=mysql_host, user=mysql_user, passwd=mysql_passwd, db=mysql_db, unix_socket=mysql_unix_socket, cursorclass=MySQLdb.cursors.DictCursor)
my_cur = my_conn.cursor()




def float_decimal(obj):
  if isinstance(obj, decimal.Decimal):
     return float(obj)
  else :
    return obj




def build_geojson(boundaries) :
  geojson = {"type": "FeatureCollection", "features": []}

  for boundary in boundaries :
    # If a unit isn't the top or the bottom of a section, it's lat/lng will be the same
    lat = boundary["lat_unit1"] if boundary["lat_unit1"] else boundary["lat_unit2"]
    lng = boundary["lng_unit1"] if boundary["lng_unit1"] else boundary["lng_unit2"]

    feature = {
      "type": "Feature", 
      "geometry": {
        "type": "Point",
        "coordinates": [
          float_decimal(lng),
          float_decimal(lat)
        ]
      },
      "properties": {
        "name": str(boundary["id"]),
        "feature_type": "gpml:UnclassifiedFeature",
        "begin_age": str(boundary["t1_age"]),
        "end_age": "0.0"
      }
    }

    geojson["features"].append(feature)

  return geojson




def chunk_boundaries(boundaries) :
  chunks = []
  
  while len(chunks) < len(boundaries)/35 :
    start_idx = len(chunks) * 35 
    chunk = build_geojson(boundaries[start_idx: start_idx + 35 ])
    chunks.append(chunk)

  # handle the remainder
  chunk = build_geojson(boundaries[len(chunks)*35: len(boundaries)])
  chunks.append(chunk)

  return chunks




def rotate_coordinates(geojson, age) :
  data = "feature_collection=" + json.dumps(geojson) + "&geologicage=" + str(age) + "&output=geojson"
  #print data
  request = urllib2.Request("http://gplates.gps.caltech.edu:8080/reconstruct_feature_collection/", data)

  try :
    response = urllib2.urlopen(request)
    output_data = response.read()
    #print output_data
    update_mysql(json.loads(output_data))
  except :
    print "----------- Error for age ", age , " -----------" 




def update_mysql(geojson) :
  for feature in geojson["features"] :
    my_cur.execute("""
      UPDATE unit_boundaries SET paleo_lat = %s, paleo_lng = %s WHERE id = %s
    """, (feature["geometry"]["coordinates"][0], feature["geometry"]["coordinates"][1], int(feature["properties"]["NAME"])))




def get_boundaries(age) :
  # Get all unit_boundaries, their columns, and coordinates (except )
  my_cur.execute("""
    SELECT ub.id, t1, t1_prop, t1_age, ub.unit_id, ub.unit_id_2, us1.col_id AS col_unit1, us2.col_id AS col_unit2, c1.lat AS lat_unit1, c1.lng AS lng_unit1, c2.lat AS lat_unit2, c2.lng AS lng_unit2  FROM unit_boundaries ub
    LEFT JOIN units_sections us1 ON ub.unit_id = us1.unit_id
    LEFT JOIN units_sections us2 ON ub.unit_id_2 = us2.unit_id
    LEFT JOIN cols c1 ON us1.col_id = c1.id
    LEFT JOIN cols c2 ON us2.col_id = c2.id
    WHERE 
      t1_age <= 540 AND 
      t1_age > 0 AND 
      t1_age = %s AND 
      (c1.project_id != 4 OR c2.project_id != 4) AND
      ub.unit_id != 0 AND
      ub.unit_id_2 != 0
    ORDER BY ub.id ASC
  """, (age,))

  return my_cur.fetchall()




# Find all distinct t1_age in unit_boundaries
my_cur.execute("""
  SELECT DISTINCT t1_age, count(*) FROM unit_boundaries WHERE t1_age <= 540 AND t1_age > 0 GROUP BY t1_age
""")
age_result = my_cur.fetchall()

# Create a flat array of these distinct t1_ages
ages = []
for age in age_result :
  ages.append(float_decimal(age["t1_age"]))

# For each distinct t1_age, get all boundaries with that t1_age
for idx, age in enumerate(ages) :
  boundaries = get_boundaries(age)

  # GPlates has a 35 point limit, so we break large sets up into chunks
  if len(boundaries) > 35 :
    chunks = chunk_boundaries(boundaries)
    for chunk in chunks :
      rotate_coordinates(chunk, age)

  else :
    geojson = build_geojson(boundaries)
    rotate_coordinates(geojson, age)

  print "Done with ", idx, " of ", len(ages)



# Update all the boundaries with a t1_age of 0
my_cur.execute("""
  UPDATE unit_boundaries, 
      (SELECT ub.id, c1.lat AS lat_unit1, c1.lng AS lng_unit1 FROM unit_boundaries ub
          LEFT JOIN units_sections us1 ON ub.unit_id = us1.unit_id
          LEFT JOIN cols c1 ON us1.col_id = c1.id
          WHERE 
            t1_age = 0 AND 
            (c1.project_id != 4)
      ) ll

  SET paleo_lat = ll.lat_unit1, paleo_lng = ll.lng_unit1
  WHERE unit_boundaries.id = ll.id
""")



