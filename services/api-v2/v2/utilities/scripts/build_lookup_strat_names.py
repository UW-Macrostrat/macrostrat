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
""")
cursor.close()
cursor = connection.cursor()

cursor.execute("""
    CREATE TABLE lookup_strat_names_new LIKE lookup_strat_names;
""")
cursor.close()
cursor = connection.cursor()


# Get all the strat names
cursor.execute("SELECT * FROM strat_names where rank != '' order by strat_name asc;")
strat_names = cursor.fetchall()


# Build hierarchy for each name
for idx, name in enumerate(strat_names):
  rank_id = name["rank"] + "_id"
  rank_name = name["rank"] + "_name"

  cursor.execute("""
    INSERT INTO lookup_strat_names_new (ref_id, concept_id, strat_name_id, strat_name, rank, """ + rank_id + """, """ + rank_name + """)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
  """, [name['ref_id'], name['concept_id'], name['id'], name['strat_name'], name['rank'], name['id'], name['strat_name']])
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
        "sgp": ["SGp", "Gp", "Fm", "Mbr", "Bed"],
        "gp": ["Gp", "Fm", "Mbr", "Bed"],
        "fm": ["Fm", "Mbr", "Bed"],
        "mbr": ["Mbr", "Bed"],
        "bed": ["Bed"]
    }

    # SELECT COUNT(*) FROM unit_strat_names WHERE strat_name_id IN (SELECT strat_name_id from lookup_strat_names where fm_id = 1205 AND rank IN ('mbr', 'bed', 'fm'))
    sql = """
      UPDATE lookup_strat_names_new SET t_units = (
        SELECT COUNT(*)
        FROM unit_strat_names
        LEFT JOIN units_sections ON unit_strat_names.unit_id = units_sections.unit_id
        LEFT JOIN cols ON units_sections.col_id = cols.id
        WHERE unit_strat_names.strat_name_id IN (
          SELECT strat_name_id
          FROM lookup_strat_names
          WHERE %s_id = %s AND rank IN """ % (name['rank'].lower(), name['id'])


    placeholders = ["%s"] * len(lookup_rank_children[name["rank"].lower()])
    sql +=  " (" + ','.join(placeholders) + ")) AND cols.status_code = 'active') WHERE strat_name_id = %s"
    params = [x for x in lookup_rank_children[name["rank"].lower()]]
    params.append(name["id"])
    cursor.execute(sql, params)
    connection.commit()
#    print idx, " of ", len(strat_names)

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

# Populate rank_name
cursor.execute("""
    UPDATE lookup_strat_names_new SET rank_name =
    CASE
    	WHEN SUBSTRING_INDEX(strat_name, ' ', -1) IN ('Suite', 'Volcanics', 'Complex', 'Melange', 'Series', 'Supersuite', 'Tongue', 'Lens', 'Lentil', 'Drift', 'Metamorphics', 'Sequence', 'Supersequence', 'Intrusives', 'Measures')
        	THEN strat_name
        WHEN LOWER(SUBSTRING_INDEX(strat_name, ' ', -1)) IN (SELECT lith FROM liths) AND rank = 'fm'
        	THEN strat_name
         WHEN SUBSTRING_INDEX(strat_name, ' ', -1) = 'Beds' AND rank = 'Bed'
            THEN strat_name
    	WHEN rank = 'SGp' THEN
        	CONCAT(strat_name, ' Supergroup')
    	WHEN rank = 'Gp' THEN
        	CONCAT(strat_name, ' Group')
        WHEN rank = 'Fm' THEN
        	CONCAT(strat_name, ' Formation')
        WHEN rank = 'Mbr' THEN
        	CONCAT(strat_name, ' Member')
        WHEN rank = 'Bed' THEN
        	CONCAT(strat_name, ' Bed')
    END
""")


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


# Populate the fields `b_period` and `t_period`
cursor.execute("""
  UPDATE lookup_strat_names_new
  SET b_period = (
    SELECT interval_name
    FROM macrostrat.intervals
    JOIN timescales_intervals ON intervals.id = timescales_intervals.interval_id
    JOIN timescales ON timescales.id = timescales_intervals.timescale_id
    WHERE age_bottom >= early_age AND age_top <= early_age
    AND timescales.id = 3
    LIMIT 1
  );
""")
connection.commit()

cursor.execute("""
  UPDATE lookup_strat_names_new
  SET t_period = (
    SELECT interval_name
    FROM intervals
    JOIN timescales_intervals ON intervals.id = timescales_intervals.interval_id
    JOIN timescales ON timescales.id = timescales_intervals.timescale_id
    WHERE age_bottom >= late_age AND age_top <= late_age
    AND timescales.id = 3
    LIMIT 1
  );
""")
connection.commit()

# Populate containing interval
cursor.execute("""
    UPDATE lookup_strat_names_new
    SET c_interval = (
        SELECT interval_name from intervals
    	JOIN timescales_intervals ON intervals.id = interval_id
    	JOIN timescales on timescale_id = timescales.id
    	WHERE timescale = 'international'
    		AND early_age > age_top
    		AND early_age <= age_bottom
    		AND late_age < age_bottom
    		AND late_age >= age_top
    		ORDER BY age_bottom - age_top
            LIMIT 1
    )
""")
connection.commit()

# Update containing interval for names not explicitly matched to units but have a concept_id
cursor.execute("""
      SELECT strat_name_id,t.age_top,b.age_bottom 
      FROM lookup_strat_names_new 
      JOIN strat_names_meta USING (concept_id) 
      JOIN intervals t on t.id=t_int 
      JOIN intervals b on b.id=b_int 
      WHERE c_interval IS NULL and t_int>0 and b_int>0;
""")
names = cursor.fetchall()

for name in names:
    cursor.execute("UPDATE lookup_strat_names_new SET c_interval= (SELECT interval_name from intervals JOIN timescales_intervals ON intervals.id = interval_id JOIN timescales on timescale_id = timescales.id WHERE timescale = 'international' AND %s > age_top AND %s <= age_bottom AND %s < age_bottom AND %s >= age_top ORDER BY age_bottom - age_top LIMIT 1) WHERE strat_name_id=%s", [name['b_age'], name['b_age'],name['t_age'],name['t_age'],name['strat_name_id']])

# alter table lookup_strat_names add column name_no_lith varchar(100);
### Remove lithological terms from strat names ###

# Get a list of lithologies
cursor.execute("""
    SELECT lith FROM liths
""")
lith_results = cursor.fetchall()
lithologies = [lith["lith"] for lith in lith_results]

# Fetch all strat names
cursor.execute("""
    SELECT strat_name_id, strat_name FROM lookup_strat_names_new
""")
strat_name_results = cursor.fetchall()

# Remove lithologies from name
for strat_name in strat_name_results:
    split_name = strat_name["strat_name"].split(" ")

    good_name = " ".join([name for name in split_name if name.lower() not in lithologies])

    cursor.execute("""
      UPDATE lookup_strat_names_new SET name_no_lith = %(name)s WHERE strat_name_id = %(strat_name_id)s
    """, {
      "name": good_name,
      "strat_name_id": strat_name["strat_name_id"]
    })


# Out with the old, in with the new
cursor.execute("TRUNCATE lookup_strat_names")
cursor.execute("INSERT INTO lookup_strat_names SELECT * FROM lookup_strat_names_new")
cursor.close()

cursor = connection.cursor()
cursor.execute("DROP TABLE lookup_strat_names_new")
cursor.close()

print "Done with lookup_strat_names table"
