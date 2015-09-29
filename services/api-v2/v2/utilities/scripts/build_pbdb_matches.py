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

## update pbdb_matches with latest pbdb data
cursor.execute("update pbdb_matches, pbdb.collections set pbdb_matches.collection_name=pbdb.collections.collection_name where pbdb_matches.collection_no=pbdb.collections.collection_no")
cursor.execute("update pbdb_matches,pbdb.coll_matrix set occs=n_occs where pbdb_matches.collection_no=coll_matrix.collection_no")
cursor.execute("update pbdb_matches,pbdb.collections set pbdb_matches.release_date=collections.release_date where pbdb_matches.collection_no=collections.collection_no")

print "Done updating pbdb_matches"

