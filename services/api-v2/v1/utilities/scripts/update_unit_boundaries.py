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

cursor.execute(""" 
  UPDATE unit_boundaries ub 
    JOIN intervals i ON ub.t1 = i.id
  SET ub.t1_age = age_bottom - ((age_bottom - age_top) * t1_prop) 
  WHERE boundary_status != 'absolute'
""")

cursor.execute(""" 
  UPDATE unit_boundaries ub 
    JOIN intervals i ON ub.t1 = i.id
  SET ub.t1_prop = (age_bottom - t1_age)/(age_bottom - age_top)
  WHERE boundary_status = 'absolute'
""")

print "Done updating unit_boundaries"
