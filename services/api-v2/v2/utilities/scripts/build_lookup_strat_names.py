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
filterwarnings("ignore", category = MySQLdb.Warning)

# Copy structure to new table
cursor.execute("""
    DROP TABLE IF EXISTS lookup_strat_names_new;
    CREATE TABLE lookup_strat_names_new LIKE lookup_strat_names;
""")
cursor.close()
cursor = connection.cursor()


# Get all the strat names
cursor.execute("SELECT * FROM strat_names where rank != '' order by strat_name asc;")
strat_names = cursor.fetchall()


# Build hierarchy for each name
for name in strat_names:
  rank_id = name["rank"] + "_id"
  rank_name = name["rank"] + "_name"

  cursor.execute("""
    INSERT INTO lookup_strat_names_new (concept_id, strat_name_id, strat_name, rank, """ + rank_id + """, """ + rank_name + """)
    VALUES (%s, %s, %s, %s, %s, %s)
  """, [name['concept_id'], name['id'], name['strat_name'], name['rank'], name['id'], name['strat_name']])
  connection.commit()

  has_parent = True
  name_id = name['id']

  while has_parent:
    # Get the parent of this unit
    cursor.execute("""
      SELECT this_name, strat_name, strat_names.id id, rank
      FROM strat_tree
      JOIN strat_names ON this_name = strat_names.id
      WHERE that_name = %s and rel = 'parent' and rank!=''
    """, [name_id])
    parent = cursor.fetchone()

    if parent is None:
      name_id = 0
    else:
      name_id = parent['id']
      parent_rank_id = parent['rank'] + "_id"
      parent_rank_name = parent['rank'] + "_name"

    if name_id > 0:
      cursor.execute("""
        UPDATE lookup_strat_names_new
        SET """ + parent_rank_id + """ = %s, """ + parent_rank_name + """ = %s
        WHERE strat_name_id = %s
      """ , [parent['id'], parent['strat_name'], name['id']])
      connection.commit()
    else :
      has_parent = False


    # Count number of units with this strat_name_id going down the hierarchy
    lookup_rank_children = {
        "sgp": ["sgp", "gp", "fm", "mbr", "bed"],
        "gp": ["gp", "fm", "mbr", "bed"],
        "fm": ["fm", "mbr", "bed"],
        "mbr": ["mbr", "bed"],
        "bed": ["bed"]
    }

    sql = "UPDATE lookup_strat_names_new SET t_units = (SELECT COUNT(*) FROM unit_strat_names WHERE strat_name_id IN ("
    sub_sql = []
    for rank in lookup_rank_children[name["rank"].lower()]:
        sub_sql.append("SELECT DISTINCT %s_id FROM lookup_strat_names WHERE %s_id = %s AND %s_id > 0" % (rank, name["rank"].lower(), name["id"], rank))
    sql += " UNION ".join(sub_sql)
    sql += ")) WHERE strat_name_id = %s"

    cursor.execute(sql, [name["id"]])
    connection.commit()

# Populate `early_age` and `late_age`
cursor.execute("""
  UPDATE lookup_strat_names_new lsn
  LEFT JOIN (
    SELECT strat_name_id, max(b_age) AS early_age, min(t_age) AS late_age
    FROM lookup_strat_names_new
    LEFT JOIN unit_strat_names USING (strat_name_id)
    LEFT JOIN lookup_unit_intervals USING (unit_id)
    GROUP BY strat_name_id
  ) AS sub USING (strat_name_id)
  SET lsn.early_age = sub.early_age, lsn.late_age = sub.late_age
""")
connection.commit()


# Populate canada_lexicon webkey from canada_lexicon
cursor.execute("UPDATE lookup_strat_names_new, canada_lexicon SET lookup_strat_names_new.gsc_lexicon = canada_lexicon.web_id WHERE lookup_strat_names_new.strat_name_id=canada_lexicon.strat_name_id")
connection.commit()


# Validate results
cursor.execute("SELECT count(*) N, (SELECT count(*) from lookup_strat_names_new) nn from strat_names WHERE rank!=''")
row = cursor.fetchone()
if row['N'] != row['nn'] :
  print "ERROR: inconsistent strat_name count in lookup table"


# Populate the fields `parent` and `tree`
cursor.execute("""
  UPDATE lookup_strat_names_new
  SET parent = CASE
    WHEN bed_id > 0 AND strat_name_id != bed_id THEN bed_id
    WHEN mbr_id > 0 AND strat_name_id != mbr_id THEN mbr_id
    WHEN fm_id > 0 AND strat_name_id != fm_id THEN fm_id
    WHEN gp_id > 0 AND strat_name_id != gp_id THEN gp_id
    WHEN sgp_id > 0 AND strat_name_id != sgp_id THEN sgp_id
    ELSE strat_name_id
  END,
    tree = CASE
    WHEN sgp_id > 0 THEN sgp_id
    WHEN gp_id > 0 THEN gp_id
    WHEN fm_id > 0 THEN fm_id
    WHEN mbr_id > 0 THEN mbr_id
    WHEN bed_id > 0 THEN bed_id
    ELSE tree = 0
  END
""")
connection.commit()


# Out with the old, in with the new
cursor.execute("TRUNCATE lookup_strat_names")
cursor.execute("INSERT INTO lookup_strat_names SELECT * FROM lookup_strat_names_new")
cursor.close()


print "Done with lookup_strat_names table"
