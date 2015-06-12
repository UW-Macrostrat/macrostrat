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


# For use later - get the top of a strat_name hierarchy
def getTopOfTree(name) :
  if name["sgp_id"] > 0 :
    return name["sgp_id"]
  elif name["gp_id"] > 0 :
    return name["gp_id"]
  elif name["fm_id"] > 0 :
    return name["fm_id"]
  elif name["mbr_id"] > 0 :
    return name["mbr_id"]
  elif name["bed_id"] > 0 :
    return name["bed_id"]
  else : 
  	return 0

# Get immediate parent
def getParent(name) :
	new_name = name.copy()
	new_name.pop(new_name['rank'].lower() + "_id", None)

	if "bed_id" in new_name and new_name["bed_id"] > 0:
		return new_name["bed_id"]
	elif "mbr_id" in new_name and new_name["mbr_id"] > 0:
		return new_name["mbr_id"]
	elif "fm_id" in new_name and new_name["fm_id"] > 0:
		return new_name["fm_id"]
	elif "gp_id" in new_name and new_name["gp_id"] > 0:
		return new_name["gp_id"]
	elif "sgp_id" in new_name and new_name["sgp_id"] > 0:
		return new_name["sgp_id"]
	else:
		return new_name["strat_name_id"]



# Create a new table
cursor.execute(""" 
	DROP TABLE IF EXISTS lookup_strat_names_new;

	CREATE TABLE lookup_strat_names_new (
		strat_name_id mediumint(8),
		strat_name varchar(100),
		rank enum('', 'SGp', 'Gp', 'Fm', 'Mbr', 'Bed'),
		rank_name varchar(20),
		bed_id mediumint(8),
		bed_name varchar(100),
		mbr_id mediumint(8),
		mbr_name varchar(100),
		fm_id mediumint(8),
		fm_name varchar(100),
		gp_id mediumint(8),
		gp_name varchar(100),
		sgp_id mediumint(8),
		sgp_name varchar(100),
		early_age decimal(8,4),
		late_age decimal(8,4),
		gsc_lexicon varchar(15),
		parent mediumint(8),
		tree mediumint(8)
	);
""")
cursor.close()
cursor = connection.cursor()

# Get all the strat names
cursor.execute("SELECT * FROM strat_names;")
strat_names = cursor.fetchall()

# Handle each name
for name in strat_names:
	nid = name['rank'] + "_id"
	n = name['rank'] + "_name"
	
	cursor.execute("INSERT INTO lookup_strat_names_new (strat_name_id, strat_name, rank, " + nid + ", " + n +") VALUES (%s, %s, %s, %s, %s)", (name['id'], name['strat_name'], name['rank'], name['id'], name['strat_name']))

	parent = 1
	old_one = name['id']

	while (parent > 0):
		# Get the parent of this unit
		cursor.execute("SELECT this_name, strat_name, strat_names.id id, rank FROM strat_tree JOIN strat_names ON this_name = strat_names.id WHERE that_name = %s and rel = 'parent'", [old_one])
		row2 = cursor.fetchone()
		
		if row2 is None:
			old_one = 0
		else:
			old_one = row2['id']
			nid = row2['rank'] + "_id"
			n = row2['rank'] + "_name"

		if old_one > 0 and parent <= 1 :
			cursor.execute("UPDATE lookup_strat_names_new SET " + nid + " = %s, "+ n +" = %s WHERE strat_name_id = %s" , [row2['id'], row2['strat_name'], name['id']])
		else :
			parent = 0
		if parent > 1:
			print "inconsistency in unit " + old_one

# build age ranges for strat_names, uses lookup table populated above for hierarchy; ages are for parent and all children unit ranges
for name in strat_names:
	nid = name['rank'] + "_id"
	cursor.execute("SELECT max(b_age) f, min(t_age) l FROM lookup_unit_intervals WHERE unit_id in (SELECT unit_id from unit_strat_names JOIN lookup_strat_names_new USING (strat_name_id) WHERE %s = %s)", [nid, name['id']])
	row2 = cursor.fetchone()

	if row2 is not None and row2['f'] is not None and row2['l'] is not None:
		cursor.execute("UPDATE lookup_strat_names_new SET early_age = %s, late_age = %s WHERE strat_name_id = %s", [row2["f"], row2["l"], row2["id"]])

# populate canada_lexicon webkey from canada_lexicon
cursor.execute("UPDATE lookup_strat_names_new, canada_lexicon SET lookup_strat_names_new.gsc_lexicon = canada_lexicon.web_id WHERE lookup_strat_names_new.strat_name_id=canada_lexicon.strat_name_id")

## validate results
cursor.execute("SELECT count(*) N, (SELECT count(*) from lookup_strat_names_new) nn from strat_names")
row = cursor.fetchone()
if row['N'] != row['nn'] :
	print "ERROR: inconsistent strat_name count in lookup table"

cursor.execute("SELECT * FROM lookup_strat_names_new")
strat_names = cursor.fetchall()

for name in strat_names:
	parent = getParent(name)
	top = getTopOfTree(name)
	cursor.execute(""" 
		UPDATE lookup_strat_names_new SET parent = %s, tree = %s WHERE strat_name_id = %s
	""", [parent, top, name["strat_name_id"]])
	connection.commit()


# Out with the old, in with the new
cursor.execute("DROP TABLE lookup_strat_names")
cursor.execute("RENAME TABLE lookup_strat_names_new TO lookup_strat_names")
cursor.close()
print "Done with lookup_strat_names table"

