import MySQLdb
import MySQLdb.cursors
from warnings import filterwarnings
import sys, os
from credentials import *

# Connect to Macrostrat
try:
  connection = MySQLdb.connect(host=mysql_host, user=mysql_user, passwd=mysql_passwd, db=mysql_db, unix_socket=mysql_unix_socket, cursorclass=MySQLdb.cursors.DictCursor)
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

# Cursor for MySQL
cursor = connection.cursor()

filterwarnings('ignore', category = MySQLdb.Warning)

csv = os.getcwd() + '/scripts/UB_full_V5V3_sectionbump.csv'

cursor.execute(""" 
DROP TABLE IF EXISTS unit_boundaries_backup_recent;
CREATE TABLE unit_boundaries_backup_recent LIKE unit_boundaries;
INSERT INTO unit_boundaries_backup_recent SELECT * FROM unit_boundaries;

TRUNCATE TABLE unit_boundaries;

LOAD DATA INFILE %(csv)s
INTO TABLE unit_boundaries 
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(t1,t1_prop,t1_age,unit_id,unit_id_2,section_id);

""", {"csv": csv})