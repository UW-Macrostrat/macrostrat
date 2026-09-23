import datetime
import time
from dataclasses import dataclass

from psycopg.sql import SQL, Identifier
from rich import print

from macrostrat.core.exc import MacrostratError
from macrostrat.database import Database

from ..database import sql_file
from ..utils import MapInfo
from .utils import find_scale_table, get_match_count, populated_fields

#: Scale tables, smallest first -- a source lives in exactly one.
SCALES = ["tiny", "small", "medium", "large"]


#: Millions of years a fuzzy-time pass will reach past the legend entry's own
#: interval, and degrees a fuzzy-space pass will reach past the column.
TIME_FUZZ_MA = 25
SPACE_BUFFER_DEGREES = 1.2


@dataclass
class MatchContext:
    """Context for a single matching pass."""

    source_id: int
    scale: str
    field: str


@dataclass
class MatchParams:
    """Context for a single matching pass."""

    strict_name: bool
    strict_space: bool
    strict_time: bool


def match_units(db: Database, map_info: MapInfo):
    source_id = map_info.id
    start = time.time()
    # Validate params!
    # Valid source_id
    result = db.run_query(
        """
        SELECT source_id
        FROM maps.sources
        WHERE source_id = :source_id
    """,
        {"source_id": source_id},
    ).first()
    if result is None:
        raise MacrostratError(f"Source {source_id} was not found in maps.sources")

    scale = find_scale_table(db, source_id)

    # Validate that this source intersects *any* Macrostrat units in space or time
    n_intersecting = db.run_query(
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

        print("      Starting unit match at ", str(datetime.datetime.now()))

        # Clean up
        db.run_sql(
            """
          DELETE FROM maps.map_units
          WHERE map_id IN (
            SELECT map_id
            FROM maps.polygons
            WHERE source_id = :source_id
              AND scale = :scale
          )
          AND basis_col NOT LIKE 'manual%'
        """,
            {
                "scale": scale,
                "source_id": source_id,
            },
        )

        print("        + Done cleaning up")

        fields = populated_fields(
            db, source_id, scale, ["strat_name", "name", "descrip", "comments"]
        )

        # Insert a new task for each matching field into the queue
        print("Processing fields", fields)
        for field in fields:
            ctx = MatchContext(source_id, scale, field)
            do_work(db, ctx)
    else:
        print("Skipping unit matching - source does not intersect any columns")

    count = get_match_count(db, source_id, Identifier("maps", "map_units"))
    print(f"Matched [bold cyan]{count}[/] units in {time.time() - start:.1f}s")


def do_work(db: Database, ctx: MatchContext):
    # Time the process
    start_time = time.time()

    print(f"      Matching units for field {ctx.field}...")

    lattice = [
        # strictName, strictSpace, strictTime
        MatchParams(True, True, True),
        MatchParams(True, False, True),
        # strict space and time
        MatchParams(False, True, True),
        MatchParams(True, True, False),
        MatchParams(False, False, True),
        MatchParams(True, False, False),
        MatchParams(False, True, False),
        MatchParams(False, False, False),
    ]

    for match_direction in ["direct", "down", "up"]:
        for params in lattice:
            _match(db, f"match-units-{match_direction}", ctx, params)

    print(f"      Done with {ctx.field} in {time.time() - start_time:.1f}s")


def _basis_col(
    field: str,
    params: MatchParams,
) -> str:
    """The `basis_col` string a pass writes, and reads back on the next one.

    Each pass excludes polygons an earlier one matched, so this doubles as
    the pass's identity. The order of the suffixes is load-bearing: the two
    precedence ladders downstream parse it back out.
    """
    basis = field
    if not params.strict_name:
        basis += "_fname"
    if not params.strict_space:
        basis += "_fspace"
    if not params.strict_time:
        basis += "_ftime"
    return basis


def _match(db: Database, procedure: str, ctx: MatchContext, params: MatchParams):
    """Run one matching pass from its SQL file.

    The only thing substituted rather than bound is `{column_geom}`, because
    strict and fuzzy space are two different expressions -- the column
    polygon against a buffered envelope of it -- and no bind can carry that.
    Every value is a bind.
    """
    db.run_sql(
        sql_file(procedure),
        {
            "scale": ctx.scale,
            "source_id": ctx.source_id,
            "match_type": _basis_col(ctx.field, params),
            "column_geom": SQL(column_geom(params.strict_space)),
            "time_fuzz": 0 if params.strict_time else TIME_FUZZ_MA,
            "space_buffer": SPACE_BUFFER_DEGREES,
        },
    )


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
