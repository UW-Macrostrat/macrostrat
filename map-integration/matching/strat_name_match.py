import argparse
import psycopg2
import psycopg2.extras
from psycopg2.extensions import AsIs
import sys
import os
import datetime
import time
import yaml

with open(os.path.join(os.path.dirname(__file__), '../credentials.yml'), 'r') as f:
    credentials = yaml.load(f)

cwd = os.path.dirname(os.path.realpath(__file__))

split_path = cwd.split("/")
split_path.pop()

sys.path.insert(0, "/".join(split_path) + "/setup")

import refresh

if __name__ == '__main__':

  connection = psycopg2.connect(dbname="burwell", user=credentials["pg_user"], host=credentials["pg_host"], port=credentials["pg_port"])
  cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

  parser = argparse.ArgumentParser(
    description="Match rocks to Macrostrat units",
    epilog="Example usage: python match_names.py --source_id 2")

  parser.add_argument("-s", "--source_id", dest="source_id",
    default="0", type=str, required=True,
    help="The ID of the desired source to match")

  arguments = parser.parse_args()

  # Validate params!
  # Valid source_id
  cursor.execute("SELECT source_id FROM maps.sources")
  sources = cursor.fetchall()
  source_ids = [source['source_id'] for source in sources]
  if int(arguments.source_id) not in source_ids:
      print "Invalid source_id argument. Source ID ", arguments.source_id, " was not found in maps.sources"
      sys.exit(1)

  # Find scale table
  scale = ""
  for scale_table in ["tiny", "small", "medium", "large"]:
      cursor.execute("SELECT * FROM maps.%(table)s WHERE source_id = %(source_id)s LIMIT 1", {
        "table": AsIs(scale_table),
        "source_id": arguments.source_id
      })
      if cursor.fetchone() is not None:
        scale = scale_table
        break

  if len(scale) < 1:
      print "Provided source_id not found in maps.small, maps.medium, or maps.large. Please insert it and try again."
      sys.exit(1)


  print 'Starting at ', str(datetime.datetime.now())


  # Clean up
  cursor.execute("""
      DELETE FROM maps.map_strat_names
      WHERE map_id IN (
        SELECT map_id
        FROM maps.%(table)s
        WHERE source_id = %(source_id)s
      ) AND basis_col NOT LIKE 'manual%%'
  """, {
      "table": AsIs(scale),
      "source_id": arguments.source_id
  })
  connection.commit()
  print "        + Done cleaning up"


  def query(strictTime, strictSpace, strictName):
      match_type = 'strat_name'

      if not strictName:
          match_type += '_fname'

      if not strictSpace:
          match_type += '_fspace'

      if strictTime == False:
          match_type += '_ftime'
      elif strictTime == None:
          match_type += '_ntime'

      cursor.execute("""
        INSERT INTO maps.map_strat_names
        SELECT unnest(map_ids), strat_name_id, %(match_type)s
        FROM (
            SELECT map_ids, lsn.strat_name_id
            FROM temp_rocks tr
            JOIN temp_names lsn on lsn.""" + ("rank_name" if strictName else "name_no_lith") + """ = tr.""" + ("strat_name" if strictName else "strat_name_clean") + """
            JOIN macrostrat.strat_name_footprints snft ON """ + ("ST_Intersects(snft.geom, tr.envelope)" if strictSpace else "ST_Intersects(ST_Buffer(snft.geom, 1.2), ST_Buffer(tr.envelope, 1.2))") + """
            JOIN macrostrat.intervals intervals_top on tr.t_interval = intervals_top.id
            JOIN macrostrat.intervals intervals_bottom on tr.b_interval = intervals_bottom.id
            WHERE ((lsn.late_age) < (intervals_bottom.age_bottom + """ + ("0" if strictTime else "25") + """))
              AND ((lsn.early_age) > (intervals_top.age_top - """ + ("0" if strictTime else "25") + """))
            and lsn.strat_name_id = snft.strat_name_id
        ) sub
      """, {
        "match_type": match_type
      })
      print "        - Done with " + match_type

  # Time the process
  start_time = time.time()

  cursor.execute("""
    DROP TABLE IF EXISTS temp_rocks;

    CREATE TABLE temp_rocks AS
    WITH first AS (
    	SELECT
    		array_agg(map_id) AS map_ids,
    		name,
    		CASE
    			WHEN
    				array_length(string_to_array(COALESCE(strat_name, ''), ';'), 1) IS NULL
    				THEN NULL
    			ELSE
    				unnest(string_to_array(COALESCE(strat_name, ''), ';'))
    			END AS strat_name,
    		age,
    		lith,
    		descrip,
    		comments,
    		t_interval,
    		b_interval,
    		ST_Envelope(ST_Collect(geom)) AS envelope
    	FROM maps.%(scale)s
    	WHERE source_id = %(source_id)s
    	GROUP BY name, strat_name, age, lith, descrip, comments, t_interval, b_interval
    ),
    name_parts AS (
    	SELECT array_to_string(map_ids, '|') AS id, a.name_part, a.nr
    	FROM first
    	LEFT JOIN LATERAL unnest(string_to_array(first.strat_name, ' '))
    	WITH ORDINALITY AS a(name_part, nr) ON TRUE
    ),
    no_liths AS (
        SELECT id, name_part
        FROM name_parts
        WHERE lower(name_part) NOT IN (select lower(lith) from macrostrat.liths) AND lower(name_part) NOT IN ('bed', 'member', 'formation', 'group', 'supergroup')
        order by nr
    ),
    clean AS (
    	SELECT id, array_to_string(array_agg(name_part), ' ') AS name
    	from no_liths
    	GROUP BY id
    )

    SELECT
    	map_ids,
    	first.name,
    	strat_name,
    	clean.name AS strat_name_clean,
    	age,
    	lith,
    	descrip,
    	comments,
    	t_interval,
    	b_interval,
    	envelope
    FROM first
    JOIN clean ON array_to_string(map_ids, '|') = id
  """, {
    "scale": AsIs(scale),
    "source_id": arguments.source_id
  })
  connection.commit()

  cursor.execute("""
    CREATE INDEX ON temp_rocks (strat_name);
    CREATE INDEX ON temp_rocks (strat_name_clean);
    CREATE INDEX ON temp_rocks (t_interval);
    CREATE INDEX ON temp_rocks (b_interval);
    CREATE INDEX ON temp_rocks USING GiST (envelope);
  """)
  connection.commit()

  cursor.execute("""
    DROP TABLE IF EXISTS temp_names;
    CREATE TABLE temp_names AS
    SELECT DISTINCT ON (sub.strat_name_id) lookup_strat_names.*
    FROM (
    	SELECT DISTINCT lsn4.strat_name_id, lsn4.strat_name, unnest(string_to_array(lsn4.rank_name, ' ')) AS words
    	FROM macrostrat.lookup_strat_names AS lsn4
    	JOIN macrostrat.strat_name_footprints ON strat_name_footprints.strat_name_id = lsn4.strat_name_id
    	JOIN maps.sources ON ST_Intersects(strat_name_footprints.geom, rgeom)
    	WHERE sources.source_id = %(source_id)s
    ) sub
    JOIN macrostrat.lookup_strat_names ON sub.strat_name_id = lookup_strat_names.strat_name_id
    WHERE words IN (
    	SELECT DISTINCT words
    	FROM (
    		SELECT DISTINCT unnest(string_to_array(strat_name, ' ')) AS words
    		FROM maps.%(scale)s
    		where source_id = %(source_id)s
    	) sub
    	WHERE lower(words) NOT IN (select lower(lith) from macrostrat.liths)
    	  AND lower(words) NOT IN ('bed', 'member', 'formation', 'group', 'supergroup')
    );
  """, {
    "scale": AsIs(scale),
    "source_id": arguments.source_id
  })
  connection.commit()

  cursor.execute("""
    CREATE INDEX ON temp_names (strat_name_id);
    CREATE INDEX ON temp_names (rank_name);
    CREATE INDEX ON temp_names (name_no_lith);
    CREATE INDEX ON temp_names (strat_name);
  """)
  connection.commit()

  elapsed = int(time.time() - start_time)
  print "        Done with prepping temp tables in ", elapsed / 60, " minutes and ", elapsed % 60, " seconds"

  # Time the process
  start_time = time.time()

  # strict time - strict space - strict name
  a = query(True, True, True)

  # strict time - fuzzy space - strict name
  b = query(True, False, True)

  # fuzzy time - strict space - strict name
  c = query(False, True, True)

  # fuzzy time - fuzzy space - strict name
  d = query(False, False, True)

  # no time - strict space - strict name
  e = query(None, True, True)

  # no time - fuzzy space - strict name
  f = query(None, False, True)

  # strict time - strict space - fuzzy name
  g = query(True, True, False)

  # strict time - fuzzy space - fuzzy name
  h = query(True, False, False)

  # fuzzy time - strict space - fuzzy name
  i = query(False, True, False)

  # fuzzy time - fuzzy space - fuzzy name
  j = query(False, False, False)

  # no time - strict space - fuzzy name
  k = query(None, True, False)

  # no time - fuzzy space - fuzzy name
  l = query(None, False, False)

  elapsed = int(time.time() - start_time)
  print "        Done with in ", elapsed / 60, " minutes and ", elapsed % 60, " seconds"
