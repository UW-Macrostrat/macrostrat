import datetime
import sys
import time

from psycopg2.extensions import AsIs
from psycopg2.extras import NamedTupleCursor, RealDictCursor
from psycopg2.sql import Identifier
from rich import print

from ..database import LegacyCommandBase, db
from ..utils import MapInfo
from .utils import get_match_count


def match_units(map: MapInfo):
    """Match a given map source to Macrostrat units.

    Populates the table maps.map_units.
    Uses all available fields of matching, including name, strat_name, descrip, and comments.
    """
    source_id = map.id
    Units().run(source_id)

    count = get_match_count(source_id, Identifier("maps", "map_units"))
    print(f"Matched [bold cyan]{count}[/] units")


class Units(LegacyCommandBase):
    source_id = None
    table = None
    field = None

    def query_down(self, strictNameMatch, strictSpace, strictTime):
        match_type = self.field

        if not strictNameMatch:
            match_type += "_fname"

        if not strictSpace:
            match_type += "_fspace"

        if not strictTime:
            match_type += "_ftime"

        self.pg["cursor"].execute(
            """
          INSERT INTO maps.map_units (map_id, unit_id, basis_col)
            WITH a AS (
                SELECT DISTINCT ON (m.map_id, concept_id) m.map_id, concept_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
                FROM maps.%(table)s m
                JOIN macrostrat.intervals intervals_top on m.t_interval = intervals_top.id
                JOIN macrostrat.intervals intervals_bottom on m.b_interval = intervals_bottom.id
                JOIN maps.map_strat_names ON m.map_id = map_strat_names.map_id
                JOIN macrostrat.lookup_strat_names on map_strat_names.strat_name_id = lookup_strat_names.strat_name_id
                WHERE m.source_id = %(source_id)s
                AND basis_col = %(match_type)s
                AND m.map_id NOT IN (
                  SELECT x.map_id
                  FROM maps.map_units x
                  JOIN maps.%(table)s z
                  ON x.map_id = z.map_id
                  WHERE z.source_id = %(source_id)s
                )
            ),
            shaped AS (
              SELECT strat_name_id, strat_name, rank,
                CASE
                    WHEN rank = 'Bed'
                      THEN '{}'
                    WHEN rank = 'Mbr'
                      THEN (SELECT COALESCE(array_agg(DISTINCT strat_name_id), '{}') FROM macrostrat.lookup_strat_names WHERE rank = 'Bed' AND mbr_id = lsn.strat_name_id)
                    WHEN rank = 'Fm'
                      THEN (SELECT COALESCE(array_agg(DISTINCT strat_name_id), '{}') FROM macrostrat.lookup_strat_names WHERE rank IN ('Bed', 'Mbr') AND fm_id = lsn.strat_name_id)
                    WHEN rank = 'Gp'
                      THEN (SELECT COALESCE(array_agg(DISTINCT strat_name_id), '{}') FROM macrostrat.lookup_strat_names WHERE rank IN ('Bed', 'Mbr', 'Fm') AND gp_id = lsn.strat_name_id)
                    WHEN rank = 'SGp'
                      THEN (SELECT COALESCE(array_agg(DISTINCT strat_name_id), '{}') FROM macrostrat.lookup_strat_names WHERE rank IN ('Bed', 'Mbr', 'Fm', 'Gp') AND sgp_id = lsn.strat_name_id)
                  END AS down
              FROM macrostrat.lookup_strat_names lsn
            ),
            flattened AS (
              SELECT strat_name_id, strat_name, rank, unnest(down) as down_names
              FROM shaped s
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
            SELECT DISTINCT ON (map_id, b.unit_id) map_id, b.unit_id AS units, %(match_type)s
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
                "table": AsIs(self.table),
                "source_id": self.source_id,
                "field": AsIs(self.field),
                "match_type": match_type,
            },
        )

        self.pg["connection"].commit()

        # print '        - Done with %s (up)' % (match_type, )

    def query_up(self, strictNameMatch, strictSpace, strictTime):
        match_type = self.field

        if not strictNameMatch:
            match_type += "_fname"

        if not strictSpace:
            match_type += "_fspace"

        if not strictTime:
            match_type += "_ftime"

        self.pg["cursor"].execute(
            """
          INSERT INTO maps.map_units (map_id, unit_id, basis_col)
            WITH a AS (
                SELECT DISTINCT ON (m.map_id, concept_id) m.map_id, concept_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
                FROM maps.%(table)s m
                JOIN macrostrat.intervals intervals_top on m.t_interval = intervals_top.id
                JOIN macrostrat.intervals intervals_bottom on m.b_interval = intervals_bottom.id
                JOIN maps.map_strat_names ON m.map_id = map_strat_names.map_id
                JOIN macrostrat.lookup_strat_names on map_strat_names.strat_name_id = lookup_strat_names.strat_name_id
                WHERE m.source_id = %(source_id)s
                AND basis_col = %(match_type)s
                AND m.map_id NOT IN (
                  SELECT x.map_id
                  FROM maps.map_units x
                  JOIN maps.%(table)s z
                  ON x.map_id = z.map_id
                  WHERE z.source_id = %(source_id)s
                )
            ),
            shaped AS (
              SELECT strat_name_id, strat_name, rank,
              (SELECT COALESCE(array_agg(u), '{}')
                FROM unnest(
                CASE
                  WHEN rank = 'Bed'
                    THEN array[mbr_id, fm_id, gp_id, sgp_id]
                  WHEN rank = 'Mbr'
                    THEN array[fm_id, gp_id, sgp_id]
                  WHEN rank = 'Fm'
                    THEN array[gp_id, sgp_id]
                  WHEN rank = 'Gp'
                    THEN array[sgp_id]
                  WHEN rank = 'SGp'
                    THEN '{}'
                END
                ) AS u WHERE u != 0
              ) AS up
              FROM macrostrat.lookup_strat_names lsn
            ),
            flattened AS (
              SELECT strat_name_id, strat_name, rank, unnest(up) as up_names
              FROM shaped s
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
            SELECT DISTINCT ON (map_id, b.unit_id) map_id, b.unit_id AS units, %(match_type)s
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
                "table": AsIs(self.table),
                "source_id": self.source_id,
                "field": AsIs(self.field),
                "match_type": match_type,
            },
        )

        self.pg["connection"].commit()

        # print '        - Done with %s (down)' % (match_type, )

    def query(self, strictNameMatch, strictSpace, strictTime):
        match_type = self.field

        if not strictNameMatch:
            match_type += "_fname"

        if not strictSpace:
            match_type += "_fspace"

        if not strictTime:
            match_type += "_ftime"

        self.pg["cursor"].execute(
            """
            INSERT INTO maps.map_units (map_id, unit_id, basis_col)
            WITH a AS (
                SELECT DISTINCT ON (m.map_id, concept_id) m.map_id, concept_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
                FROM maps.%(table)s m
                JOIN macrostrat.intervals intervals_top on m.t_interval = intervals_top.id
                JOIN macrostrat.intervals intervals_bottom on m.b_interval = intervals_bottom.id
                JOIN maps.map_strat_names ON m.map_id = map_strat_names.map_id
                JOIN macrostrat.lookup_strat_names on map_strat_names.strat_name_id = lookup_strat_names.strat_name_id
                WHERE m.source_id = %(source_id)s
                AND basis_col = %(match_type)s
                AND m.map_id NOT IN (
                  SELECT x.map_id
                  FROM maps.map_units x
                  JOIN maps.%(table)s z
                  ON x.map_id = z.map_id
                  WHERE z.source_id = %(source_id)s
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
            SELECT DISTINCT ON (map_id, b.unit_id) map_id, b.unit_id AS units, %(match_type)s
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
                "table": AsIs(self.table),
                "source_id": self.source_id,
                "field": AsIs(self.field),
                "match_type": match_type,
            },
        )

        self.pg["connection"].commit()

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
        if source_id == "--help" or source_id == "-h":
            print(Units.__doc__)
            sys.exit()

        start = time.time()
        Units.source_id = source_id
        # Validate params!
        # Valid source_id
        self.pg["cursor"].execute(
            """
            SELECT source_id
            FROM maps.sources
            WHERE source_id = %(source_id)s
        """,
            {"source_id": source_id},
        )
        result = self.pg["cursor"].fetchone()
        if result is None:
            print("Invalid source_id. %s was not found in maps.sources" % (source_id,))
            sys.exit(1)

        # Find scale table
        scale = ""
        for scale_table in ["tiny", "small", "medium", "large"]:
            self.pg["cursor"].execute(
                """
            SELECT map_id
            FROM maps.%(table)s
            WHERE source_id = %(source_id)s
            LIMIT 1
        """,
                {"table": AsIs(scale_table), "source_id": source_id},
            )
            if self.pg["cursor"].fetchone() is not None:
                scale = scale_table
                break

        if len(scale) == 0:
            print(
                "Provided source_id not found in maps.small, maps.medium, or maps.large. Please insert it and try again."
            )
            sys.exit(1)

        # Validate that this source intersects *any* Macrostrat units in space or time
        self.pg["cursor"].execute(
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
            WHERE source_id = %(source_id)s
        """,
            {"source_id": source_id},
        )

        if self.pg["cursor"].fetchone()[0] > 0:
            # skip this
            # TODO cleanup this jank assignment
            Units.table = scale

            print("      Starting unit match at ", str(datetime.datetime.now()))

            # Clean up
            self.pg["cursor"].execute(
                """
              DELETE FROM maps.map_units
              WHERE map_id IN (
                SELECT map_id
                FROM maps.%(table)s
                WHERE source_id = %(source_id)s
              )
              AND basis_col NOT LIKE 'manual%%'
            """,
                {"table": AsIs(scale), "source_id": source_id},
            )

            self.pg["connection"].commit()
            print("        + Done cleaning up")

            # Fields in burwell to match on
            fields = ["strat_name", "name", "descrip", "comments"]

            # Filter null fields
            self.pg["cursor"].execute(
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
            result = self.pg["cursor"].fetchone()

            for key, val in result._asdict().items():
                if val == 0:
                    field_name = key
                    fields = [d for d in fields if d != key]
                    print("        + Excluding %s because it is null" % (field_name,))

            # Insert a new task for each matching field into the queue
            print("Processing fields", fields)
            for field in fields:
                Units.do_work(self, field)
        else:
            print("Skipping unit matching - source does not intersect any columns")
