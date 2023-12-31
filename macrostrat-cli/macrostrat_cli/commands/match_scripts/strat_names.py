from psycopg2.extensions import AsIs
from psycopg2.extras import NamedTupleCursor
import time
import datetime
import sys
from ..base import Base


class StratNames(Base):
    """
    macrostrat match strat_names <source_id>:
        Match a given map source's `strat_name` field to Macrostrat strat_name_ids.
        Populates the table maps.map_strat_names

    Usage:
      macrostrat match strat_names <source_id>
      macrostrat match strat_names -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat match strat_names 123
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """

    meta = {
        "mariadb": False,
        "pg": True,
        "usage": """
            Matches the stratigraphic name field of geologic maps to Macrostrat strat names
        """,
        "required_args": {"source_id": "A valid source_id"},
    }

    source_id = None

    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)

    def query(self, strictTime, strictSpace, strictName):
        match_type = "strat_name"

        if not strictName:
            match_type += "_fname"

        if not strictSpace:
            match_type += "_fspace"

        if strictTime == False:
            match_type += "_ftime"
        elif strictTime == None:
            match_type += "_ntime"

        macroNameMatch = "rank_name" if strictName else "name_no_lith"
        mapNameMatch = "strat_name" if strictName else "strat_name_clean"

        # Relax the matching constraints
        spaceQuery = (
            "ST_Intersects(snft.geom, tr.envelope)"
            if strictSpace
            else "ST_Intersects(ST_Buffer(snft.geom, 1.2), ST_Buffer(tr.envelope, 1.2))"
        )
        # Time buffer
        timeFuzz = "0" if strictTime else "25"

        where = ""

        if strictTime == None:
            where = "lsn.strat_name_id = snft.strat_name_id"
        else:
            where = (
                """((lsn.late_age) < (intervals_bottom.age_bottom + """
                + (timeFuzz)
                + """))
                AND ((lsn.early_age) > (intervals_top.age_top - """
                + (timeFuzz)
                + """))
                and lsn.strat_name_id = snft.strat_name_id"""
            )

        # Handle no time in the query!!!
        self.pg["cursor"].execute(
            """
            INSERT INTO maps.map_strat_names
            SELECT unnest(map_ids), lsn.strat_name_id, %(match_type)s
            FROM temp_rocks tr
            JOIN temp_names lsn on lsn."""
            + (macroNameMatch)
            + """ = tr."""
            + (mapNameMatch)
            + """
            JOIN macrostrat.strat_name_footprints snft ON """
            + (spaceQuery)
            + """
            JOIN macrostrat.intervals intervals_top on tr.t_interval = intervals_top.id
            JOIN macrostrat.intervals intervals_bottom on tr.b_interval = intervals_bottom.id
            WHERE %(where)s
        """,
            {"match_type": match_type, "where": AsIs(where)},
        )
        self.pg["connection"].commit()

        # print '        - Done with %s' % (match_type, )

    def run(self, source_id):
        if source_id == "--help" or source_id == "-h":
            print(StratNames.__doc__)
            sys.exit()

        # Time the process
        start_time = time.time()

        # Validate params!
        # Valid source_id
        self.pg["cursor"].execute(
            """
            SELECT source_id
            FROM maps.sources
            WHERE source_id = %(source_id)s
        """,
            {"source_id": int(source_id)},
        )
        sources = self.pg["cursor"].fetchall()

        if len(sources) != 1:
            print(
                "Invalid source_id argument. Source ID %s was not found in maps.sources"
                % (source_id,)
            )
            sys.exit(1)

        # Find scale table
        scale = ""
        for scale_table in ["tiny", "small", "medium", "large"]:
            self.pg["cursor"].execute(
                "SELECT map_id FROM maps.%(table)s WHERE source_id = %(source_id)s LIMIT 1",
                {"table": AsIs(scale_table), "source_id": int(source_id)},
            )
            if self.pg["cursor"].fetchone() is not None:
                scale = scale_table
                break

        if len(scale) < 1:
            print(
                "Provided source_id not found in maps.small, maps.medium, or maps.large. Please insert it and try again."
            )
            sys.exit(1)

        print("      Starting strat name match at ", str(datetime.datetime.now()))

        # Clean up
        self.pg["cursor"].execute(
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
        self.pg["connection"].commit()
        print("        + Done cleaning up")

        self.pg["cursor"].execute(
            """
            DROP TABLE IF EXISTS temp_rocks;

            CREATE TABLE temp_rocks AS
            WITH first AS (
            	SELECT
            	    row_number() OVER() as row_no,
            		array_agg(map_id) AS map_ids,
            		name,
            		string_to_array(strat_name, ';') AS strat_name,
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
            	    row_no,
            		name,
            		row_number() OVER() as name_no
                FROM (
                    SELECT row_no, unnest(strat_name) AS name
                    FROM first
                ) foo
            ),
            name_parts AS (
            	SELECT row_no, name_no, a.name_part, a.nr
            	FROM with_nos
            	LEFT JOIN LATERAL unnest(string_to_array(with_nos.name, ' '))
            	WITH ORDINALITY AS a(name_part, nr) ON TRUE
            ),
            no_liths AS (
                SELECT row_no, name_no, name_part
                FROM name_parts
                WHERE lower(name_part) NOT IN (select lower(lith) from macrostrat.liths) AND lower(name_part) NOT IN ('bed', 'member', 'formation', 'group', 'supergroup')
                order by nr
            ),
            clean AS (
            	SELECT row_no, name_no, trim(array_to_string(array_agg(name_part), ' ')) AS name
            	from no_liths
            	GROUP BY name_no, row_no
            )

            SELECT
            	map_ids,
            	first.name,
            	first.strat_name as orig_strat_name,
            	trim(both ' ' FROM replace(clean.name, '.', '')) AS strat_name,
            	trim(both ' ' FROM clean.name) AS strat_name_clean,
            	age,
            	lith,
            	descrip,
            	comments,
            	t_interval,
            	b_interval,
            	envelope
            FROM first
            LEFT JOIN clean ON first.row_no = clean.row_no;
        """,
            {"scale": AsIs(scale), "source_id": source_id},
        )
        self.pg["connection"].commit()

        self.pg["cursor"].execute(
            """
            CREATE INDEX ON temp_rocks (strat_name);
            CREATE INDEX ON temp_rocks (strat_name_clean);
            CREATE INDEX ON temp_rocks (t_interval);
            CREATE INDEX ON temp_rocks (b_interval);
            CREATE INDEX ON temp_rocks USING GiST (envelope);
        """
        )
        self.pg["connection"].commit()

        self.pg["cursor"].execute(
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
        self.pg["connection"].commit()

        self.pg["cursor"].execute(
            """
            CREATE INDEX ON temp_names (strat_name_id);
            CREATE INDEX ON temp_names (rank_name);
            CREATE INDEX ON temp_names (name_no_lith);
            CREATE INDEX ON temp_names (strat_name);
        """
        )
        self.pg["connection"].commit()

        elapsed = int(time.time() - start_time)
        # print '        Done with prepping temp tables in ', elapsed / 60, ' minutes and ', elapsed % 60, ' seconds'

        # Time the process
        start_time = time.time()

        # strict time - strict space - strict name
        a = StratNames.query(self, True, True, True)

        # strict time - fuzzy space - strict name
        b = StratNames.query(self, True, False, True)

        # fuzzy time - strict space - strict name
        c = StratNames.query(self, False, True, True)

        # fuzzy time - fuzzy space - strict name
        d = StratNames.query(self, False, False, True)

        # no time - strict space - strict name
        e = StratNames.query(self, None, True, True)

        # no time - fuzzy space - strict name
        f = StratNames.query(self, None, False, True)

        # strict time - strict space - fuzzy name
        g = StratNames.query(self, True, True, False)

        # strict time - fuzzy space - fuzzy name
        h = StratNames.query(self, True, False, False)

        # fuzzy time - strict space - fuzzy name
        i = StratNames.query(self, False, True, False)

        # fuzzy time - fuzzy space - fuzzy name
        j = StratNames.query(self, False, False, False)

        # no time - strict space - fuzzy name
        k = StratNames.query(self, None, True, False)

        # no time - fuzzy space - fuzzy name
        l = StratNames.query(self, None, False, False)

        elapsed = int(time.time() - start_time)
        print(
            "        Done with in ",
            elapsed / 60,
            " minutes and ",
            elapsed % 60,
            " seconds",
        )
