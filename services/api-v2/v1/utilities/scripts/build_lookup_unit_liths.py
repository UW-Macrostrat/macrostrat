import MySQLdb
import MySQLdb.cursors
from warnings import filterwarnings
import sys
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

# recompute and populate comp_prop

cursor.execute("SELECT  a.unit_id, adom sub_lith,bdom dom_lith FROM (SELECT unit_id,count(id) adom, dom from unit_liths WHERE dom='sub' group by unit_id) a JOIN (SELECT unit_id,count(id) bdom, dom from unit_liths WHERE dom='dom' group by unit_id) b on b.unit_id=a.unit_id")
numrows = cursor.rowcount
row = cursor.fetchall()

for x in xrange(0,numrows):
	n=row[x]['sub_lith']+(row[x]['dom_lith']*5)
	dom_p=5/n
	sub_p=1/n
	cursor.execute("UPDATE unit_liths set comp_prop=%f WHERE unit_id=%d and dom='dom'" % (dom_p,row[x]['unit_id']))
	cursor.execute("UPDATE unit_liths set comp_prop=%f WHERE unit_id=%d and dom='sub'" % (sub_p,row[x]['unit_id']))

# truncate the lookup table
cursor.execute("TRUNCATE TABLE lookup_unit_liths")

# initial query for simple lith summary
cursor.execute("INSERT INTO lookup_unit_liths (unit_id,lith_short) SELECT unit_id, GROUP_CONCAT(lith,' ',comp_prop SEPARATOR '|') FROM unit_liths JOIN liths on lith_id=liths.id GROUP BY unit_id")

# build the long lithology summary 
cursor.execute("TRUNCATE TABLE temp_liths")
cursor.execute("INSERT INTO temp_liths SELECT unit_id, GROUP_CONCAT(lith_att SEPARATOR ' '), lith, comp_prop FROM unit_liths LEFT JOIN unit_liths_atts ON unit_lith_id=unit_liths.id LEFT JOIN lith_atts ON lith_att_id=lith_atts.id LEFT JOIN liths on lith_id=liths.id GROUP BY unit_liths.id")
cursor.execute("UPDATE lookup_unit_liths JOIN (SELECT unit_id, GROUP_CONCAT(lith_atts,' ',lith,' ',comp_prop SEPARATOR '|') ee FROM temp_liths WHERE lith_atts IS NOT NULL GROUP BY unit_id) oo ON oo.unit_id=lookup_unit_liths.unit_id SET lith_long=oo.ee")
cursor.execute("UPDATE lookup_unit_liths JOIN (SELECT unit_id, GROUP_CONCAT(lith,' ',comp_prop SEPARATOR '|') ee FROM temp_liths WHERE lith_atts IS NULL GROUP BY unit_id) oo ON oo.unit_id=lookup_unit_liths.unit_id SET lith_long=oo.ee")
cursor.execute("UPDATE lookup_unit_liths JOIN (SELECT sp.unit_id, GROUP_CONCAT(sp.lith_class, ' ', sp.comp_prop  SEPARATOR '|') lith_class FROM (SELECT unit_id,lith_class, round(sum(comp_prop),3) comp_prop from unit_liths JOIN liths on lith_id=liths.id GROUP BY unit_id,lith_class) sp GROUP BY sp.unit_id) lithclass ON lithclass.unit_id=lookup_unit_liths.unit_id SET lookup_unit_liths.lith_class=lithclass.lith_class")
cursor.execute("UPDATE lookup_unit_liths JOIN (SELECT sp.unit_id, GROUP_CONCAT(sp.lith_type, ' ', sp.comp_prop  SEPARATOR '|') lith_type FROM (SELECT unit_id,lith_type, round(sum(comp_prop),3) comp_prop from unit_liths JOIN liths on lith_id=liths.id GROUP BY unit_id,lith_type) sp GROUP BY sp.unit_id) lithclass ON lithclass.unit_id=lookup_unit_liths.unit_id SET lookup_unit_liths.lith_type=lithclass.lith_type")

# handle environments
cursor.execute("UPDATE lookup_unit_liths JOIN (SELECT unit_id, GROUP_CONCAT(environ SEPARATOR '|') ee,  GROUP_CONCAT(distinct environ_type SEPARATOR '|') ff, GROUP_CONCAT(distinct environ_class SEPARATOR '|') gg FROM unit_environs JOIN environs on environ_id=environs.id GROUP BY unit_id) AS o ON o.unit_id=lookup_unit_liths.unit_id SET environ= o.ee, environ_type=o.ff, environ_class=o.gg")

cursor.execute("UPDATE lookup_unit_liths set environ='inferred marine' , environ_class='marine' WHERE lith_class like 'sedimentary' and environ like ''")

## validate results
cursor.execute("SELECT count(*) N, (SELECT count(*) from lookup_unit_liths) nn from units")
row = cursor.fetchone()
if row['N'] != row['nn'] :
	print "ERROR: inconsistent unit count in lookup_unit_liths table"

print "Done with lookup_unit_liths table"








