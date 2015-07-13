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

# Copy structure to new table
cursor.execute("CREATE TABLE lookup_usgs_strat_names_new LIKE lookup_usgs_strat_names")

# initial query
cursor.execute("SELECT * FROM usgs_strat_names where rank not like '' and dont_use=0")
numrows = cursor.rowcount
row = cursor.fetchall()

# initialize arrays
row2 = {}

#handle each unit
for x in xrange(0,numrows):
	#print row[x]['id']
	nid = row[x]['rank'] + "_id"
	n = row[x]['rank'] + "_name"
	
	cursor.execute("INSERT INTO lookup_usgs_strat_names_new (gsc_lexicon,usgs_strat_name_id,strat_name,rank, " + nid + ", " + n +") VALUES (%s, %s, %s, %s, %s, %s)", (row[x]['usgs_id'], row[x]['id'], row[x]['strat_name'], row[x]['rank'], row[x]['id'], row[x]['strat_name']))

	parent = 1
	old_one = row[x]['id']

	while (parent > 0):
		cursor.execute("SELECT this_name,strat_name,usgs_strat_names.id id, rank FROM usgs_strat_tree JOIN usgs_strat_names ON this_name = usgs_strat_names.id WHERE rank not like '' and that_name = %d and rel='parent'" % (old_one))
		row2 = cursor.fetchone()
		
		if row2 is None:
			old_one = 0
		else:
			old_one = row2['id']
			nid = row2['rank'] + "_id"
			n = row2['rank'] + "_name"

		if old_one > 0 and parent <= 1 and nid != "_id":
			cursor.execute("UPDATE lookup_usgs_strat_names_new SET " + nid + " = %s, "+ n +" = %s WHERE usgs_strat_name_id = %s" , (row2['id'], row2['strat_name'], row[x]['id']))
		else :
			parent = 0
		if parent > 1:
			print "inconsistency in unit " + old_one

# build age ranges for usgs_strat_names, uses lookup table populated above for hierarchy; ages are for parent and all children unit ranges
cursor.execute("SELECT * FROM usgs_strat_names")
numrows = cursor.rowcount
row = cursor.fetchall()

row2 = {}

## validate results
cursor.execute("SELECT count(*) N, (SELECT count(*) from lookup_usgs_strat_names_new) nn from usgs_strat_names where rank!=''")
row = cursor.fetchone()
if row['N'] != row['nn'] :
	print "ERROR: inconsistent strat_name count in lookup table"

# Out with the old, in with the new
cursor.execute("DROP TABLE lookup_usgs_strat_names")
cursor.execute("RENAME TABLE lookup_usgs_strat_names_new TO lookup_usgs_strat_names")

print "Done with lookup_usgs_strat_names table"

