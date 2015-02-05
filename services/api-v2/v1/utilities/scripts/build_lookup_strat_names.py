import MySQLdb
import MySQLdb.cursors
import urllib2
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

###############################################################################################
## build lookup_strat_names
###############################################################################################
# truncate the table
cursor.execute("TRUNCATE TABLE lookup_strat_names")

# initial query
cursor.execute("SELECT * FROM strat_names")
numrows = cursor.rowcount
row = cursor.fetchall()

# initialize arrays
row2={}

#handle each unit
for x in xrange(0,numrows):
	#print row[x]['id']
	nid = row[x]['rank'] + "_id"
	n = row[x]['rank'] + "_name"
	
	cursor.execute("INSERT INTO lookup_strat_names (strat_name_id,strat_name,rank, "+ nid +", "+ n +") VALUES (%s, %s, %s, %s, %s)", (row[x]['id'], row[x]['strat_name'], row[x]['rank'], row[x]['id'], row[x]['strat_name']))

	parent = 1
	old_one = row[x]['id']

	while (parent > 0):
		cursor.execute("SELECT this_name,strat_name,strat_names.id id, rank FROM strat_tree JOIN strat_names ON this_name=strat_names.id WHERE that_name = %d and rel='parent'" % (old_one))
		row2=cursor.fetchone()
		
		if row2 is None:
			old_one = 0
		else:
			old_one = row2['id']
			nid = row2['rank'] + "_id"
			n = row2['rank'] + "_name"

		if old_one > 0 and parent <= 1 :
			cursor.execute("UPDATE lookup_strat_names SET "+ nid +" = %s, "+ n +" = %s WHERE strat_name_id = %s" , (row2['id'], row2['strat_name'], row[x]['id']))
		else :
			parent = 0
		if parent > 1:
			print "inconsistency in unit " + old_one

# build age ranges for strat_names, uses lookup table populated above for hierarchy; ages are for parent and all children unit ranges
cursor.execute("SELECT * FROM strat_names")
numrows = cursor.rowcount
row = cursor.fetchall()

row2={}

for x in xrange(0,numrows):
	nid = row[x]['rank'] + "_id"
	cursor.execute("SELECT max(FO_age) f, min(LO_age) l FROM lookup_unit_intervals WHERE unit_id in (SELECT unit_id from unit_strat_names JOIN lookup_strat_names USING (strat_name_id) WHERE %s = %d)" % (nid, row[x]['id']))
	row2 = cursor.fetchone()

	if row2 is not None and row2['f'] is not None and row2['l'] is not None:
		cursor.execute("UPDATE lookup_strat_names SET early_age = %f, late_age = %f WHERE strat_name_id=%d" % (row2['f'], row2['l'], row[x]['id']))

## validate results
cursor.execute("SELECT count(*) N, (SELECT count(*) from lookup_strat_names) nn from strat_names")
row = cursor.fetchone()
if row['N'] != row['nn'] :
	print "ERROR: inconsistent strat_name count in lookup table"

print "Done with lookup_strat_names table"

