import os
import psycopg2
import sys
import urllib
import json

sys.path = [os.path.join(os.path.dirname(__file__), os.pardir)] + sys.path
import credentials

conn = psycopg2.connect(dbname=credentials.pg_db, user=credentials.pg_user, host=credentials.pg_host, port=credentials.pg_port)
cur = conn.cursor()

cur.execute("select distinct unit_link, unit_com, unitdesc, unit_name, u_rocktype1, u_rocktype2, u_rocktype3 from sources.gmus where (unit_com is null or unitdesc is null or unit_name is null) and unit_link is not null")
unit_links = cur.fetchall()

def clean(field) :
  field = field.replace('\"', '')
  field = field.strip()
  field = " ".join(field.split())

  return field

for unit_link in unit_links :
  print unit_link[0]
  req = urllib.urlopen('http://mrdata.usgs.gov/geology/state/sgmc-unit.php?unit=' + unit_link[0] + '&f=JSON')

  if req.getcode() != 200 :
    print "------ Bad request for ", unit_link[0], " ------"
    continue

  data = json.loads(req.read())

  sql = []
  params = {
    "unit_link": unit_link[0]
  }

  if "unit_name" in data and unit_link[3] is None:
    sql.append("unit_name = %(unit_name)s")
    params["unit_name"] = clean(data["unit_name"])

  if "unitdesc" in data and unit_link[2] is None:
    sql.append("unitdesc = %(unitdesc)s")
    params["unitdesc"] = clean(data["unitdesc"])

  if "unit_com" in data and unit_link[1] is None:
    sql.append("unit_com = %(unit_com)s")
    params["unit_com"] = clean(data["unit_com"])

  if "rocktype" in data and (unit_link[4] is None or unit_link[5] is None or unit_link[6] is None):
      for rocktype in data["rocktype"]:
          if rocktype["importance"] == 1 and unit_link[4] is None:
              sql.append("u_rocktype1 = %(u_rocktype1)s")
              params["u_rocktype1"] = rocktype["text"]

          elif rocktype["importance"] == 2 and unit_link[5] is None:
              sql.append("u_rocktype2 = %(u_rocktype2)s")
              params["u_rocktype2"] = rocktype["text"]

          elif rocktype["importance"] == 3 and unit_link[6] is None:
              sql.append("u_rocktype3 = %(u_rocktype3)s")
              params["u_rocktype3"] = rocktype["text"]


  if len(sql) > 0:
      cur.execute("UPDATE sources.gmus SET " + ", ".join(sql) + "  WHERE unit_link = %(unit_link)s", params)
      conn.commit()
