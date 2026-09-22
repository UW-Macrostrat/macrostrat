import datetime
import time

from psycopg2.sql import Identifier
from rich import print

from macrostrat.core.exc import MacrostratError

from ..database import get_database
from ..utils import MapInfo
from .utils import find_scale_table, get_match_count, populated_fields

#: Scale tables, smallest first -- a source lives in exactly one.
SCALES = ["tiny", "small", "medium", "large"]


def match_units(map: MapInfo):
    """Match a given map source to Macrostrat units.

    Populates the table maps.map_units.
    Uses all available fields of matching, including name, strat_name, descrip, and comments.
    """
    db = get_database()
    source_id = map.id
    Units(db).run(source_id)

    count = get_match_count(db, source_id, Identifier("maps", "map_units"))
    print(f"Matched [bold cyan]{count}[/] units")


class Units:
    def __init__(self, db):
        self.db = db
        self.source_id = None
        self.table = None
        self.field = None

    def query_down(self, strictNameMatch, strictSpace, strictTime):
        match_type = self.field

        if not strictNameMatch:
            match_type += "_fname"

        if not strictSpace:
            match_type += "_fspace"

        if not strictTime:
            match_type += "_ftime"

        self.db.run_sql(
            """
          INSERT INTO maps.map_units (map_id, unit_id, basis_col)
            WITH a AS (
                SELECT DISTINCT ON (m.map_id, concept_id) m.map_id, concept_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
                FROM {scale_table} m
                JOIN macrostrat.intervals intervals_top on m.t_interval = intervals_top.id
                JOIN macrostrat.intervals intervals_bottom on m.b_interval = intervals_bottom.id
                JOIN maps.map_strat_names ON m.map_id = map_strat_names.map_id
                JOIN macrostrat.lookup_strat_names on map_strat_names.strat_name_id = lookup_strat_names.strat_name_id
                WHERE m.source_id = :source_id
                AND basis_col = :match_type
                AND NOT EXISTS (
                  SELECT 1
                  FROM maps.map_units x
                  WHERE x.map_id = m.map_id
                )
            ),
            flattened AS (
              /* The rank tree is flattened once by the lexicon rebuild. This
                 walked `lookup_strat_names` with four correlated subqueries per
                 row, on every matching pass -- up to sixty-four full-lexicon
                 scans for one source. */
              SELECT lsn.strat_name_id, lsn.strat_name, lsn.rank,
                     unnest(tree.descendant_ids) AS down_names
              FROM macrostrat.lookup_strat_names lsn
              JOIN macrostrat.lookup_strat_name_tree tree
                ON tree.strat_name_id = lsn.strat_name_id
            ),
            b AS (
            SELECT
              flattened.strat_name_id AS match_strat_name_id,
              flattened.strat_name AS match_strat_name,
              flattened.rank AS match_rank,
              lookup_strat_names.strat_name,
              unit_strat_names.strat_name_id,
              unit_strat_names.unit_id,
              lookup_unit_intervals.t_age,
              lookup_unit_intervals.b_age,
              """
            + (
                "cols.poly_geom "
                if strictSpace
                else "st_buffer(st_envelope(cols.poly_geom), 1.2)"
            )
            + """ AS geom
            FROM macrostrat.unit_strat_names
            JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
            JOIN macrostrat.cols ON units_sections.col_id = cols.id
            JOIN macrostrat.lookup_unit_intervals ON unit_strat_names.unit_id = lookup_unit_intervals.unit_id
            JOIN flattened ON flattened.down_names = unit_strat_names.strat_name_id
            JOIN macrostrat.lookup_strat_names ON flattened.down_names = lookup_strat_names.strat_name_id
            WHERE cols.status_code='active'
            )
            SELECT DISTINCT ON (map_id, b.unit_id) map_id, b.unit_id AS units, :match_type
            FROM a
            JOIN b ON a.strat_name_id = b.match_strat_name_id
            WHERE ST_Intersects(a.geom, b.geom)
                AND ((b.t_age) < (a.age_bottom + """
            + ("0" if strictTime else "25")
            + """))
                AND ((b.b_age) > (a.age_top - """
            + ("0" if strictTime else "25")
            + """));
        """,
            {
                "scale_table": Identifier("maps", self.table),
                "source_id": self.source_id,
                "match_type": match_type,
            },
        )

        # print '        - Done with %s (up)' % (match_type, )

    def query_up(self, strictNameMatch, strictSpace, strictTime):
        match_type = self.field

        if not strictNameMatch:
            match_type += "_fname"

        if not strictSpace:
            match_type += "_fspace"

        if not strictTime:
            match_type += "_ftime"

        self.db.run_sql(
            """
          INSERT INTO maps.map_units (map_id, unit_id, basis_col)
            WITH a AS (
                SELECT DISTINCT ON (m.map_id, concept_id) m.map_id, concept_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
                FROM {scale_table} m
                JOIN macrostrat.intervals intervals_top on m.t_interval = intervals_top.id
                JOIN macrostrat.intervals intervals_bottom on m.b_interval = intervals_bottom.id
                JOIN maps.map_strat_names ON m.map_id = map_strat_names.map_id
                JOIN macrostrat.lookup_strat_names on map_strat_names.strat_name_id = lookup_strat_names.strat_name_id
                WHERE m.source_id = :source_id
                AND basis_col = :match_type
                AND NOT EXISTS (
                  SELECT 1
                  FROM maps.map_units x
                  WHERE x.map_id = m.map_id
                )
            ),
            flattened AS (
              /* The rank tree is flattened once by the lexicon rebuild. This
                 walked `lookup_strat_names` with four correlated subqueries per
                 row, on every matching pass -- up to sixty-four full-lexicon
                 scans for one source. */
              SELECT lsn.strat_name_id, lsn.strat_name, lsn.rank,
                     unnest(tree.descendant_ids) AS down_names
              FROM macrostrat.lookup_strat_names lsn
              JOIN macrostrat.lookup_strat_name_tree tree
                ON tree.strat_name_id = lsn.strat_name_id
            ),
            b AS (
            SELECT
              flattened.strat_name_id AS match_strat_name_id,
              flattened.strat_name AS match_strat_name,
              flattened.rank AS match_rank,
              lookup_strat_names.strat_name,
              unit_strat_names.strat_name_id,
              unit_strat_names.unit_id,
              lookup_unit_intervals.t_age,
              lookup_unit_intervals.b_age,
              """
            + (
                "cols.poly_geom "
                if strictSpace
                else "st_buffer(st_envelope(cols.poly_geom), 1.2)"
            )
            + """ AS geom
            FROM macrostrat.unit_strat_names
            JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
            JOIN macrostrat.cols ON units_sections.col_id = cols.id
            JOIN macrostrat.lookup_unit_intervals ON unit_strat_names.unit_id = lookup_unit_intervals.unit_id
            JOIN flattened ON flattened.up_names = unit_strat_names.strat_name_id
            JOIN macrostrat.lookup_strat_names ON flattened.up_names = lookup_strat_names.strat_name_id
            WHERE cols.status_code='active'
            )
            SELECT DISTINCT ON (map_id, b.unit_id) map_id, b.unit_id AS units, :match_type
            FROM a
            JOIN b ON a.strat_name_id = b.match_strat_name_id
            WHERE ST_Intersects(a.geom, b.geom)
                AND ((b.t_age) < (a.age_bottom + """
            + ("0" if strictTime else "25")
            + """))
                AND ((b.b_age) > (a.age_top - """
            + ("0" if strictTime else "25")
            + """));
        """,
            {
                "scale_table": Identifier("maps", self.table),
                "source_id": self.source_id,
                "match_type": match_type,
            },
        )

        # print '        - Done with %s (down)' % (match_type, )

    def query(self, strictNameMatch, strictSpace, strictTime):
        match_type = self.field

        if not strictNameMatch:
            match_type += "_fname"

        if not strictSpace:
            match_type += "_fspace"

        if not strictTime:
            match_type += "_ftime"

        self.db.run_sql(
            """
            INSERT INTO maps.map_units (map_id, unit_id, basis_col)
            WITH a AS (
                SELECT DISTINCT ON (m.map_id, concept_id) m.map_id, concept_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
                FROM {scale_table} m
                JOIN macrostrat.intervals intervals_top on m.t_interval = intervals_top.id
                JOIN macrostrat.intervals intervals_bottom on m.b_interval = intervals_bottom.id
                JOIN maps.map_strat_names ON m.map_id = map_strat_names.map_id
                JOIN macrostrat.lookup_strat_names on map_strat_names.strat_name_id = lookup_strat_names.strat_name_id
                WHERE m.source_id = :source_id
                AND basis_col = :match_type
                AND NOT EXISTS (
                  SELECT 1
                  FROM maps.map_units x
                  WHERE x.map_id = m.map_id
                )
            ),
                b AS (
                  SELECT unit_strat_names.strat_name_id, unit_strat_names.unit_id, lookup_unit_intervals.t_age, lookup_unit_intervals.b_age, """
            + (
                "cols.poly_geom "
                if strictSpace
                else "st_buffer(st_envelope(cols.poly_geom), 1.2)"
            )
            + """ AS geom
                  FROM macrostrat.unit_strat_names
                  JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
                  JOIN macrostrat.cols ON units_sections.col_id = cols.id
                  JOIN macrostrat.lookup_unit_intervals ON unit_strat_names.unit_id = lookup_unit_intervals.unit_id
                  WHERE strat_name_id IN (SELECT DISTINCT strat_name_id FROM a) AND cols.status_code='active'
                )
            SELECT DISTINCT ON (map_id, b.unit_id) map_id, b.unit_id AS units, :match_type
            FROM a
            JOIN b ON a.strat_name_id = b.strat_name_id
            WHERE ST_Intersects(a.geom, b.geom)
                AND ((b.t_age) < (a.age_bottom + """
            + ("0" if strictTime else "25")
            + """))
                AND ((b.b_age) > (a.age_top - """
            + ("0" if strictTime else "25")
            + """));
        """,
            {
                "scale_table": Identifier("maps", self.table),
                "source_id": self.source_id,
                "match_type": match_type,
            },
        )

        # print '        - Done with %s' % (match_type, )

    def match(self):
        # strictName, strictSpace, strictTime, useNullSet

        # Strict name, strict space, strict time
        a = Units.query(self, True, True, True)

        # Strict name, fuzzy space, strict time
        b = Units.query(self, True, False, True)

        # Fuzzy name, strict space, strict time
        c = Units.query(self, False, True, True)

        # Strict name, strict space, fuzzy time
        d = Units.query(self, True, True, False)

        # Fuzzy name, fuzzy space, strict time
        e = Units.query(self, False, False, True)

        # Strict name, fuzzy space, fuzzy time
        f = Units.query(self, True, False, False)

        # Fuzzy name, strict space, fuzzy time
        g = Units.query(self, False, True, False)

        # Fuzzy name, fuzzy space, fuzzy time
        h = Units.query(self, False, False, False)

    def match_down(self):
        # strictName, strictSpace, strictTime, useNullSet

        # Strict name, strict space, strict time
        a = Units.query_down(self, True, True, True)

        # Strict name, fuzzy space, strict time
        b = Units.query_down(self, True, False, True)

        # Fuzzy name, strict space, strict time
        c = Units.query_down(self, False, True, True)

        # Strict name, strict space, fuzzy time
        d = Units.query_down(self, True, True, False)

        # Fuzzy name, fuzzy space, strict time
        e = Units.query_down(self, False, False, True)

        # Strict name, fuzzy space, fuzzy time
        f = Units.query_down(self, True, False, False)

        # Fuzzy name, strict space, fuzzy time
        g = Units.query_down(self, False, True, False)

        # Fuzzy name, fuzzy space, fuzzy time
        h = Units.query_down(self, False, False, False)

    def match_up(self):
        # strictName, strictSpace, strictTime

        # Strict name, strict space, strict time
        a = Units.query_up(self, True, True, True)

        # Strict name, fuzzy space, strict time
        b = Units.query_up(self, True, False, True)

        # Fuzzy name, strict space, strict time
        c = Units.query_up(self, False, True, True)

        # Strict name, strict space, fuzzy time
        d = Units.query_up(self, True, True, False)

        # Fuzzy name, fuzzy space, strict time
        e = Units.query_up(self, False, False, True)

        # Strict name, fuzzy space, fuzzy time
        f = Units.query_up(self, True, False, False)

        # Fuzzy name, strict space, fuzzy time
        g = Units.query_up(self, False, True, False)

        # Fuzzy name, fuzzy space, fuzzy time
        h = Units.query_up(self, False, False, False)

    def do_work(self, field):
        # Time the process
        start_time = time.time()

        print("      * Working on ", field, " *")

        self.field = field

        Units.match(self)
        Units.match_down(self)
        Units.match_up(self)

        elapsed = int(time.time() - start_time)
        print(
            "        Done with ",
            self.field,
            " in ",
            elapsed / 60,
            " minutes and ",
            elapsed % 60,
            " seconds",
        )

    def run(self, source_id):
        start = time.time()
        self.source_id = source_id
        # Validate params!
        # Valid source_id
        result = self.db.run_query(
            """
            SELECT source_id
            FROM maps.sources
            WHERE source_id = :source_id
        """,
            {"source_id": source_id},
        ).first()
        if result is None:
            raise MacrostratError(f"Source {source_id} was not found in maps.sources")

        scale = find_scale_table(self.db, source_id)

        # Validate that this source intersects *any* Macrostrat units in space or time
        n_intersecting = self.db.run_query(
            """
            SELECT count(units.id)
            FROM maps.sources
            JOIN (
                SELECT units.id, b_age, t_age, ST_Buffer(ST_Envelope(poly_geom), 1.2) as poly_geom
                FROM macrostrat.units
                JOIN macrostrat.lookup_unit_intervals ON lookup_unit_intervals.unit_id = units.id
                JOIN macrostrat.units_sections ON units.id = units_sections.unit_id
                JOIN macrostrat.cols ON macrostrat.cols.id = units_sections.col_id
                WHERE macrostrat.cols.status_code='active'
            ) units ON ST_Intersects(poly_geom, rgeom)
            WHERE source_id = :source_id
        """,
            {"source_id": source_id},
        ).scalar()

        if n_intersecting > 0:
            # skip this
            # TODO cleanup this jank assignment
            self.table = scale

            print("      Starting unit match at ", str(datetime.datetime.now()))

            # Clean up
            self.db.run_sql(
                """
              DELETE FROM maps.map_units
              WHERE map_id IN (
                SELECT map_id
                FROM {scale_table}
                WHERE source_id = :source_id
              )
              AND basis_col NOT LIKE 'manual%'
            """,
                {
                    "scale_table": Identifier("maps", scale),
                    "source_id": source_id,
                },
            )

            print("        + Done cleaning up")

            fields = populated_fields(
                self.db, source_id, scale, ["strat_name", "name", "descrip", "comments"]
            )

            # Insert a new task for each matching field into the queue
            print("Processing fields", fields)
            for field in fields:
                self.do_work(field)
        else:
            print("Skipping unit matching - source does not intersect any columns")
