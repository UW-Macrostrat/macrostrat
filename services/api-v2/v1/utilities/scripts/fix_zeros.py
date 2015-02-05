import MySQLdb
import MySQLdb.cursors
import sys
import urllib
import json
from credentials import *

# Connect to Macrostrat
try:
  conn = MySQLdb.connect(host=mysql_host, user=mysql_user, passwd=mysql_passwd, db=mysql_db, unix_socket=mysql_unix_socket, cursorclass=MySQLdb.cursors.DictCursor)
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()


# Get a single unit from the API
def getUnit(id) :
  if id != 0:
    req = urllib.urlopen("http://localhost:5000/api/units?response=long&id=" + str(id))
    data = json.loads(req.read())

    u = data["success"]["data"]
    return u[0]
  else :
    return {}

def updateBoundaries(boundaries) :
  for boundary in boundaries :
    cur.execute("""
      UPDATE unit_boundaries ub
      JOIN intervals i ON ub.t1 = i.id
      SET t1_prop = %s, 
      t1_age = i.age_bottom - ((i.age_bottom - i.age_top) * %s)
      WHERE ub.id = %s;""", [boundary["new_t1_prop"], boundary["new_t1_prop"], boundary["id"]])
    conn.commit()



def fixInsideUnit(unit) :
  zero = getUnit(unit["id"])
  cur.execute("SELECT * FROM unit_boundaries WHERE unit_id = %s", [unit["id"]])
  r = cur.fetchall()
  zero["t1"] = r[0]["t1"]
  # 0. Find unit that surrounds zero
  ep = list(set(zero["units_above"]).intersection(zero["units_below"]))[0]

  # 1. Get all unit_boundaries with zero's top + bottom contact
  cur.execute("SELECT * FROM unit_boundaries WHERE unit_id = %s OR unit_id_2 = %s", [ep, ep])
  boundaries = cur.fetchall()

  same_t1 = True

  # 2A. Check if all the boundaries have the same t1 or not
  for boundary in boundaries :
    for boundary2 in boundaries :
      if boundary["t1"] != boundary2["t1"] :
        same_t1 = False

  # 2B.
  max_prop = -1
  min_prop = 99

  if same_t1 :
    for boundary in boundaries :
      if boundary["t1_prop"] > max_prop :
        max_prop = boundary["t1_prop"]

      if boundary["t1_prop"] < min_prop :
        min_prop = boundary["t1_prop"]

  else :
    max_prop = 1
    for boundary in boundaries :
      if boundary["t1"] == zero["t1"] and boundary["t1_prop"] < min_prop :
        min_prop = boundary["t1_prop"]

  # 3. Get our new proportions
  delta = (max_prop - min_prop)/2

  new_min_prop = ((delta - min_prop)/2) + min_prop
  new_max_prop = ((max_prop - delta)/2) + delta

  # 4A. Get boundary where unit_id_2 = zero's id
  top_boundary_of_zero = {}
  bottom_boundary_of_zero = {}
  for boundary in boundaries :
    if boundary["unit_id_2"] == zero["id"] : 
      top_boundary_of_zero = boundary

    if boundary["unit_id"] == zero["id"] :
      bottom_boundary_of_zero = boundary

  top_boundary_of_zero["new_t1_prop"] = new_max_prop
  bottom_boundary_of_zero["new_t1_prop"] = new_min_prop

  if len(zero["units_below"]) < 2 and len(zero["units_above"]) < 2 :
    print "(Inside unit) Fixed ", zero["id"]
    updateBoundaries([bottom_boundary_of_zero, top_boundary_of_zero])
  else :
    not_fixed += 1

# Cursor for MySQL
cur = conn.cursor()

# Find problematic units (i.e. those with a duration of 0Ma)
cur.execute("SELECT id, maxage,minage FROM (select units.id, min(ub1.t1_age) minage, max(ub2.t1_age) maxage from units JOIN unit_boundaries ub1 on units.id=ub1.unit_id JOIN unit_boundaries ub2 ON units.id=ub2.unit_id_2 group by units.id) bigone WHERE maxage=minage", [])
#cur.execute("SELECT * FROM units WHERE id = %s LIMIT 1", [33983])

# Fetch the results
problematicas = cur.fetchall()

# Count the number that were not fixed
not_fixed = 0

# For each of the problematic units...
for zero in problematicas:
    # This is the unit_id of the unit
    unit = getUnit(zero["id"])

    if len(unit["units_above"]) > 1 or len(unit["units_below"]) > 1:
      print "Don't wanna touch ", zero["id"]
      not_fixed += 1
      continue
    # Create a hash for the units above and below this given unit
    contacts_above = {};
    contacts_below = {};

    # 0. Get and record data for all units above and below
    for contact in unit["units_above"] :
      data = getUnit(contact)
      if len(data) > 0:
        contacts_above[data["id"]] = data

    for contact in unit["units_below"] :
      data = getUnit(contact)
      if len(data) > 0:
        contacts_below[data["id"]] = data

    is_inside = False
    # 1. Make sure it's top and bottom contacts don't contact each other 
    for contact in unit["units_above"] :
      if contact in contacts_below :
        if contacts_below[contact]["t_age"] == contacts_below[contact]["b_age"] :
          not_fixed += 1
          print "Skip this mofo"
        else :
          fixInsideUnit(zero)
        
        is_inside = True
        #raise Exception("units_above contact units_below")

    if is_inside :
      continue

    for contact in unit["units_below"] :
      if contact in contacts_above :
        if contacts_above[contact]["t_age"] == contacts_above[contact]["b_age"] :
          not_fixed += 1
          print "Skip this mofo"
        else :
          fixInsideUnit(zero)

        is_inside = True
        #raise Exception("units_below contact units_above")

    if is_inside :
      continue
    # 2. Get all unit_boundaries that contain our problematic unit
    cur.execute("SELECT * FROM unit_boundaries WHERE unit_id = %s OR unit_id_2 = %s", [unit["id"], unit["id"]])
    boundaries = cur.fetchall()

    #print boundaries

    up_or_down = ""


    #3. Verify that all boundaries in which our problematic unit is present have the same t1 and t1_prop
    for boundary in boundaries :
      for boundary2 in boundaries:
        if boundary["t1"] != boundary2["t1"]:
          raise Exception("Different t1s!")
        if boundary2["t1_prop"] != boundary2["t1_prop"] :
          raise Exception("Different t1_props!")


    # Figure out if our problematic unit should absorb space from above ("go_up") or below ("go_down")
    for boundary in boundaries:
      # Find contacts where our unit is the top contact
      if boundary["unit_id_2"] == unit["id"] :
        if boundary["t1_prop"] == 0:
          up_or_down = "go_up"
        else :
          up_or_down = "go_down"

    #print up_or_down

    # Get the bottom/top_contact proportions + ages
    if up_or_down == "go_down" :
      # placeholders is simply our parameters in our parameterized query
      placeholders = ""
      for contact in unit["units_below"] :
        placeholders += "%s,"

      # Remove the trailing comma...
      placeholders = placeholders[:-1]

      # Get all boundaries where the problematic unit's bottom contacts are the "above" units
      cur.execute("SELECT * FROM unit_boundaries WHERE unit_id_2 IN (" + placeholders + ")", unit["units_below"] )
      bs = cur.fetchall()

      min_age = 9999;
      target = ""

      # Find the minimum age of these boundaries
      for boundary in bs :
        if boundary["t1_age"] < min_age :
          min_age = boundary["t1_age"]

### TODO: Clean up this ^ and below

      # Find the boundary that has this minimum age
      for boundary in bs :
        if boundary["t1_age"] == min_age :
          target = boundary

      # 5. Compare target boundary and unit boundary
      
      boundaries_to_update = []
      for boundary in boundaries :
        # Find all the boundaries where our problematic unit is the unit_above
        if boundary["unit_id_2"] == zero["id"]:
          boundaries_to_update.append(boundary)

        # For convinience, find the boundary between our target and problematic
        if boundary["unit_id"] == target["unit_id_2"] and boundary["unit_id_2"] == zero["id"] :
          unit_target_boundary = boundary
 

      if unit_target_boundary["t1"] == target["t1"] :
        # find the difference of their proportions and divide by 2
        new_prop = ((unit_target_boundary["t1_prop"] - target["t1_prop"])/2) + target["t1_prop"]
      else :
        # They are in different intervals
        new_prop = (unit_target_boundary["t1_prop"]/2) if unit_target_boundary["t1_prop"]/2 != 0 else 0.5
      
      # Add the new proportion to all the boundaries that need to be updated (all the ones where the problematic unit is the unit_id_2, aka "above")
      for boundary in boundaries_to_update :
        boundary["new_t1_prop"] = new_prop

      # We have our new proportion!
      
      if new_prop != 0 :
        print "Fixed ", zero["id"]
        # Update the database
        updateBoundaries(boundaries_to_update)
      else :
        not_fixed += 1


    # Else we're going up
    else :
      placeholders = ""
      for contact in unit["units_above"] :
        placeholders += "%s,"

      placeholders = placeholders[:-1]

      cur.execute("SELECT * FROM unit_boundaries WHERE unit_id IN (" + placeholders + ")", unit["units_above"] )
      bs = cur.fetchall()

      max_age = -1;
      target = ""

      # Find the boundary with the greatest t1_age (target)
      for boundary in bs :
        if boundary["t1_age"] > max_age :
          max_age = boundary["t1_age"]

      for boundary in bs :

        if boundary["t1_age"] == max_age :
          target = boundary


      boundaries_to_update = []

      # 5. Compare target boundary and unit boundary
      for boundary in boundaries :
        if boundary["unit_id"] == zero["id"] :
          boundaries_to_update.append(boundary)

        if boundary["unit_id"] == zero["id"] and boundary["unit_id_2"] == target["unit_id"] :
          unit_target_boundary = boundary

      #print unit_target_boundary
      #print target

      if unit_target_boundary["t1"] == target["t1"] :
        #print target, unit_target_boundary
        # find the difference of their proportions and divide by 2
        new_prop = ((target["t1_prop"] - unit_target_boundary["t1_prop"])/2) + unit_target_boundary["t1_prop"]
      else :
        # They are in different intervals
        new_prop = (unit_target_boundary["t1_prop"]/2) if unit_target_boundary["t1_prop"]/2 != 0 else 0.5

      
      # Add the new proportion to all the boundaries that need to be updated (all the ones where the problematic unit is the unit_id, aka "below")
      for boundary in boundaries_to_update :
        boundary["new_t1_prop"] = new_prop

      # We have our new proportion!
      #print boundaries_to_update
      

      if new_prop != 0 :
        print "Fixed ", zero["id"]
        # Update the database
        updateBoundaries(boundaries_to_update)
      else :
        not_fixed += 1

print "Of ", len(problematicas), " zero-duration units, ", not_fixed, " were not fixed"
    # SELECT ub.id, ub.t1, ub.t1_prop, ub.t1_age, i.age_bottom - ((i.age_bottom - i.age_top)*ub.t1_prop) AS computed_t1_age FROM `unit_boundaries` ub JOIN intervals i ON ub.t1 = i.id

