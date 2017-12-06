from psycopg2.extensions import AsIs
from psycopg2.extras import NamedTupleCursor
import time
import datetime
import sys

class StratNames:
    meta = {
        'mariadb': False,
        'pg': True,
        'usage': """
            Matches the stratigraphic name field of geologic maps to Macrostrat strat names
        """,
        'required_args': {
            'source_id': 'A valid source_id'
        }
    }

    source_id = None
    connection = None
    cursor = None

    def __init__(self, pgConnection):
        StratNames.connection = pgConnection()
        StratNames.cursor = StratNames.connection.cursor(cursor_factory = NamedTupleCursor)


    @classmethod
    def query(self, strictTime, strictSpace, strictName):
        match_type = 'strat_name'

        if not strictName:
            match_type += '_fname'

        if not strictSpace:
            match_type += '_fspace'

        if strictTime == False:
            match_type += '_ftime'
        elif strictTime == None:
            match_type += '_ntime'

        macroNameMatch = 'rank_name' if strictName else 'name_no_lith'
        mapNameMatch = 'strat_name' if strictName else 'strat_name_clean'

        spaceQuery = 'ST_Intersects(snft.geom, tr.envelope)' if strictSpace else 'ST_Intersects(ST_Buffer(snft.geom, 1.2), ST_Buffer(tr.envelope, 1.2))'
        timeFuzz = '0' if strictTime else '25'

        where = ''

        if strictTime == None:
            where = 'lsn.strat_name_id = snft.strat_name_id'
        else:
            where = """((lsn.late_age) < (intervals_bottom.age_bottom + """ + (timeFuzz) + """))
                AND ((lsn.early_age) > (intervals_top.age_top - """ + (timeFuzz) + """))
                and lsn.strat_name_id = snft.strat_name_id"""
        # Handle no time in the query!!!
        StratNames.cursor.execute("""
            INSERT INTO maps.map_strat_names
            SELECT unnest(map_ids), strat_name_id, %(match_type)s
            FROM (
                SELECT map_ids, lsn.strat_name_id
                FROM temp_rocks tr
                JOIN temp_names lsn on lsn.""" + (macroNameMatch) + """ = tr.""" + (mapNameMatch) + """
                JOIN macrostrat.strat_name_footprints snft ON """ + (spaceQuery) + """
                JOIN macrostrat.intervals intervals_top on tr.t_interval = intervals_top.id
                JOIN macrostrat.intervals intervals_bottom on tr.b_interval = intervals_bottom.id
                WHERE %(where)s
            ) sub
        """, {
            'match_type': match_type,
            'where': AsIs(where)
        })
        StratNames.connection.commit()

        print '        - Done with %s' % (match_type, )


    @staticmethod
    def build(source_id):
        # Time the process
        start_time = time.time()

        # Validate params!
        # Valid source_id
        StratNames.cursor.execute("""
            SELECT source_id
            FROM maps.sources
            WHERE source_id = %(source_id)s
        """, { 'source_id': int(source_id) })
        sources = StratNames.cursor.fetchall()

        if len(sources) != 1:
            print 'Invalid source_id argument. Source ID %s was not found in maps.sources' % (source_id, s)
            sys.exit(1)

        # Find scale table
        scale = ""
        for scale_table in ["tiny", "small", "medium", "large"]:
          StratNames.cursor.execute("SELECT * FROM maps.%(table)s WHERE source_id = %(source_id)s LIMIT 1", {
            'table': AsIs(scale_table),
            'source_id': source_id
          })
          if StratNames.cursor.fetchone() is not None:
            scale = scale_table
            break

        if len(scale) < 1:
          print 'Provided source_id not found in maps.small, maps.medium, or maps.large. Please insert it and try again.'
          sys.exit(1)


        print 'Starting at ', str(datetime.datetime.now())


        # Clean up
        StratNames.cursor.execute("""
          DELETE FROM maps.map_strat_names
          WHERE map_id IN (
            SELECT map_id
            FROM maps.%(table)s
            WHERE source_id = %(source_id)s
          ) AND basis_col NOT LIKE 'manual%%'
        """, {
          'table': AsIs(scale),
          'source_id': source_id
        })
        StratNames.connection.commit()
        print '        + Done cleaning up'

        StratNames.cursor.execute("""
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
            with_nos AS (
            	SELECT
            		row_number() OVER() as row_no,
            		*
            	FROM first
            ),
            name_parts AS (
            	SELECT row_no, array_to_string(map_ids, '|') AS id, a.name_part, a.nr
            	FROM with_nos
            	LEFT JOIN LATERAL unnest(string_to_array(with_nos.strat_name, ' '))
            	WITH ORDINALITY AS a(name_part, nr) ON TRUE
            ),
            no_liths AS (
                SELECT id, row_no, name_part
                FROM name_parts
                WHERE lower(name_part) NOT IN (select lower(lith) from macrostrat.liths) AND lower(name_part) NOT IN ('bed', 'member', 'formation', 'group', 'supergroup')
                order by nr
            ),
            clean AS (
            	SELECT id, row_no, array_to_string(array_agg(name_part), ' ') AS name
            	from no_liths
            	GROUP BY row_no, id
            )
            SELECT
            	map_ids,
            	with_nos.name,
            	trim(both ' ' FROM replace(strat_name, '.', '')) AS strat_name,
            	trim(both ' ' FROM clean.name) AS strat_name_clean,
            	age,
            	lith,
            	descrip,
            	comments,
            	t_interval,
            	b_interval,
            	envelope
            FROM with_nos
            JOIN clean ON with_nos.row_no = clean.row_no
        """, {
            'scale': AsIs(scale),
            'source_id': source_id
        })
        StratNames.connection.commit()

        StratNames.cursor.execute("""
            CREATE INDEX ON temp_rocks (strat_name);
            CREATE INDEX ON temp_rocks (strat_name_clean);
            CREATE INDEX ON temp_rocks (t_interval);
            CREATE INDEX ON temp_rocks (b_interval);
            CREATE INDEX ON temp_rocks USING GiST (envelope);
        """)
        StratNames.connection.commit()

        StratNames.cursor.execute("""
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
            'scale': AsIs(scale),
            'source_id': source_id
        })
        StratNames.connection.commit()

        StratNames.cursor.execute("""
            CREATE INDEX ON temp_names (strat_name_id);
            CREATE INDEX ON temp_names (rank_name);
            CREATE INDEX ON temp_names (name_no_lith);
            CREATE INDEX ON temp_names (strat_name);
        """)
        StratNames.connection.commit()

        elapsed = int(time.time() - start_time)
        print '        Done with prepping temp tables in ', elapsed / 60, ' minutes and ', elapsed % 60, ' seconds'

        # Time the process
        start_time = time.time()

        # strict time - strict space - strict name
        a = StratNames.query(True, True, True)

        # strict time - fuzzy space - strict name
        b = StratNames.query(True, False, True)

        # fuzzy time - strict space - strict name
        c = StratNames.query(False, True, True)

        # fuzzy time - fuzzy space - strict name
        d = StratNames.query(False, False, True)

        # no time - strict space - strict name
        e = StratNames.query(None, True, True)

        # no time - fuzzy space - strict name
        f = StratNames.query(None, False, True)

        # strict time - strict space - fuzzy name
        g = StratNames.query(True, True, False)

        # strict time - fuzzy space - fuzzy name
        h = StratNames.query(True, False, False)

        # fuzzy time - strict space - fuzzy name
        i = StratNames.query(False, True, False)

        # fuzzy time - fuzzy space - fuzzy name
        j = StratNames.query(False, False, False)

        # no time - strict space - fuzzy name
        k = StratNames.query(None, True, False)

        # no time - fuzzy space - fuzzy name
        l = StratNames.query(None, False, False)

        elapsed = int(time.time() - start_time)
        print '        Done with in ', elapsed / 60, ' minutes and ', elapsed % 60, ' seconds'
