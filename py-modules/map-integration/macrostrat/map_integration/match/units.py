import datetime
import time

from psycopg.sql import SQL, Identifier
from rich import print

from macrostrat.core.exc import MacrostratError

from ..database import get_database, sql_file
from ..utils import MapInfo
from .utils import find_scale_table, get_match_count, populated_fields

#: Scale tables, smallest first -- a source lives in exactly one.
SCALES = ["tiny", "small", "medium", "large"]


#: Millions of years a fuzzy-time pass will reach past the legend entry's own
#: interval, and degrees a fuzzy-space pass will reach past the column.
TIME_FUZZ_MA = 25
SPACE_BUFFER_DEGREES = 1.2


def column_geom(strict_space: bool) -> str:
    """The column geometry a pass compares against.

    Two different expressions rather than one expression with a different
    number -- strict tests the column polygon itself, fuzzy tests a buffered
    envelope of it -- so the choice of shape stays in Python while the distance
    is bound. Changing that (testing a zero-buffered envelope in both cases, to
    make it one expression) would alter which geometry the strict pass uses, and
    spatial rewrites here are not made without benchmarking.
    """
    if strict_space:
        return "cols.poly_geom "
    return "ST_Buffer(ST_Envelope(cols.poly_geom), :space_buffer)"


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

    def _basis_col(
        self, strict_name: bool, strict_space: bool, strict_time: bool
    ) -> str:
        """The `basis_col` string a pass writes, and reads back on the next one.

        Each pass excludes polygons an earlier one matched, so this doubles as
        the pass's identity. The order of the suffixes is load-bearing: the two
        precedence ladders downstream parse it back out.
        """
        basis = self.field
        if not strict_name:
            basis += "_fname"
        if not strict_space:
            basis += "_fspace"
        if not strict_time:
            basis += "_ftime"
        return basis

    def _match(self, procedure: str, strict_name, strict_space, strict_time):
        """Run one matching pass from its SQL file.

        The only thing substituted rather than bound is `{column_geom}`, because
        strict and fuzzy space are two different expressions -- the column
        polygon against a buffered envelope of it -- and no bind can carry that.
        Every value is a bind.
        """
        self.db.run_sql(
            sql_file(procedure),
            {
                "scale_table": Identifier("maps", self.table),
                "source_id": self.source_id,
                "match_type": self._basis_col(strict_name, strict_space, strict_time),
                "column_geom": SQL(column_geom(strict_space)),
                "time_fuzz": 0 if strict_time else TIME_FUZZ_MA,
                "space_buffer": SPACE_BUFFER_DEGREES,
            },
        )

    def query_down(self, strictNameMatch, strictSpace, strictTime):
        self._match("match-units-down", strictNameMatch, strictSpace, strictTime)

    def query_up(self, strictNameMatch, strictSpace, strictTime):
        self._match("match-units-up", strictNameMatch, strictSpace, strictTime)

    def query(self, strictNameMatch, strictSpace, strictTime):
        self._match("match-units-direct", strictNameMatch, strictSpace, strictTime)

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
                SELECT units.id, b_age, t_age,
                       ST_Buffer(ST_Envelope(poly_geom), :space_buffer) as poly_geom
                FROM macrostrat.units
                JOIN macrostrat.lookup_unit_intervals ON lookup_unit_intervals.unit_id = units.id
                JOIN macrostrat.units_sections ON units.id = units_sections.unit_id
                JOIN macrostrat.cols ON macrostrat.cols.id = units_sections.col_id
                WHERE macrostrat.cols.status_code='active'
            ) units ON ST_Intersects(poly_geom, rgeom)
            WHERE source_id = :source_id
        """,
            {"source_id": source_id, "space_buffer": SPACE_BUFFER_DEGREES},
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
