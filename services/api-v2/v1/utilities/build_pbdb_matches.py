import MySQLdb
import MySQLdb.cursors
import urllib2
import sys

# Connect to Macrostrat
try:
  connection = MySQLdb.connect(host="", user="", passwd="", db="", unix_socket="/var/tmp/mariadb.sock", cursorclass=MySQLdb.cursors.DictCursor)
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

# Cursor for MySQL
cursor = connection.cursor()

###############################################################################################
## update pbdb_matches with latest pbdb data
###############################################################################################

cursor.execute("update pbdb_matches, pbdb.collections set pbdb_matches.collection_name=pbdb.collections.collection_name where pbdb_matches.collection_no=pbdb.collections.collection_no")
cursor.execute("update pbdb_matches,pbdb.coll_matrix set occs=n_occs where pbdb_matches.collection_no=coll_matrix.collection_no")
cursor.execute("update pbdb_matches,pbdb.collections set pbdb_matches.release_date=collections.release_date where pbdb_matches.collection_no=collections.collection_no")

print "Done updating pbdb_matches"

