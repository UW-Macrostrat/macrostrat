import multiprocessing
from .match_names_multi import *
import psycopg2
import psycopg2.extras
from psycopg2.extensions import AsIs
import sys
import os
import datetime
from typer import Argument, Option

from ...database import db

cwd = os.path.dirname(os.path.realpath(__file__))

split_path = cwd.split("/")
split_path.pop()
split_path.pop()

sys.path.insert(0, "/".join(split_path) + "/setup")


def match_names(
    source_id: int = Argument(..., help="The ID of the desired source to match"),
    exclude: str = Option(
        "",
        help="Field(s) that should be ommitted from the matching process. Ex: --exclude descrip,comments",
    ),
):
    """Match rocks to Macrostrat units"""
    connection = db.engine.raw_connection()
    cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Validate params!
    # Valid source_id
    cursor.execute("SELECT source_id FROM maps.sources")
    sources = cursor.fetchall()
    source_ids = [source["source_id"] for source in sources]
    if source_id not in source_ids:
        print(
            "Invalid source_id argument. Source ID ",
            source_id,
            " was not found in maps.sources",
        )
        sys.exit(1)

    # Find scale table
    scale = ""
    for scale_table in ["tiny", "small", "medium", "large"]:
        cursor.execute(
            "SELECT * FROM maps.%(table)s WHERE source_id = %(source_id)s LIMIT 1",
            {"table": AsIs(scale_table), "source_id": source_id},
        )
        if cursor.fetchone() is not None:
            scale = scale_table
            break

    if len(scale) < 1:
        print(
            "Provided source_id not found in maps.small, maps.medium, or maps.large. Please insert it and try again."
        )
        sys.exit(1)

    print("Starting at ", str(datetime.datetime.now()))

    # Clean up
    cursor.execute(
        """
      DELETE FROM maps.map_strat_names
      WHERE map_id IN (
        SELECT map_id
        FROM maps.%(table)s
        WHERE source_id = %(source_id)s
      ) AND basis_col NOT LIKE 'manual%%'
  """,
        {"table": AsIs(scale), "source_id": source_id},
    )
    connection.commit()
    print("        + Done cleaning up")

    tasks = multiprocessing.JoinableQueue()
    results = multiprocessing.Queue()

    num_processors = 1
    if multiprocessing.cpu_count() < 4:
        num_processors = multiprocessing.cpu_count()
    else:
        num_processors = 4

    processors = [Processor(tasks, results) for i in range(num_processors)]

    for each in processors:
        each.start()

    ### Define our tasks ###

    # Fields in burwell to match on
    fields = ["strat_name", "name", "descrip", "comments"]

    # Remove the fields explicitly excluded
    exclude = exclude.split(",")
    if len(exclude) > 0:
        for field in exclude:
            try:
                fields.remove(field)
            except:
                print("        + Not excluding invalid field selection ", field)

    # Filter null fields
    cursor.execute(
        """
    SELECT
        count(distinct strat_name)::int AS strat_name,
        count(distinct name)::int AS name,
        count(distinct descrip)::int AS descrip,
        count(distinct comments)::int AS comments
    FROM maps.%(scale)s where source_id = %(source_id)s;
  """,
        {"scale": AsIs(scale), "source_id": source_id},
    )
    result = cursor.fetchone()

    for field in result:
        if result[field] == 0:
            fields.remove(field)
            print("        + Excluding", field, "because it is null")

    cursor.execute(
        """
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
  """,
        {"scale": AsIs(scale), "source_id": source_id},
    )
    connection.commit()

    cursor.execute(
        """
    CREATE INDEX ON temp_rocks (strat_name);
    CREATE INDEX ON temp_rocks (strat_name_clean);
    CREATE INDEX ON temp_rocks (t_interval);
    CREATE INDEX ON temp_rocks (b_interval);
    CREATE INDEX ON temp_rocks USING GiST (envelope);
  """
    )
    connection.commit()

    cursor.execute(
        """
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
  """,
        {"scale": AsIs(scale), "source_id": source_id},
    )
    connection.commit()

    cursor.execute(
        """
    CREATE INDEX ON temp_names (strat_name_id);
    CREATE INDEX ON temp_names (rank_name);
    CREATE INDEX ON temp_names (name_no_lith);
    CREATE INDEX ON temp_names (strat_name);
  """
    )
    connection.commit()

    # Insert a new task for each matching field into the queue
    for field in fields:
        tasks.put(Task(scale, source_id, field))

    for i in range(num_processors):
        tasks.put(None)

    tasks.join()
