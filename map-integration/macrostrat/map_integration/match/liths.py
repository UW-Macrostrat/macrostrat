import sys
import time

from psycopg2.extensions import AsIs
from psycopg2.extras import NamedTupleCursor
from psycopg2.sql import Identifier
from rich import print

from ..database import LegacyCommandBase, db
from ..utils import MapInfo
from .utils import get_match_count


def match_liths(map: MapInfo):
    """
    Match a given map source to Macrostrat lithologies.
    Populates the table maps.legend_liths.
    Uses all available fields of matching, including lith, name, strat_name, descrip, and comments.
    """
    Liths().run(map.id)

    counts = get_lith_count(map.id)
    mlc = counts["map_liths"]
    llc = counts["legend_liths"]
    print(f"Matched [bold cyan]{llc}[/] legend liths ([bold cyan]{mlc}[/] map liths)")


def get_lith_count(source_id: int):
    # Not sure where this gets created to be honest...
    map_liths_count = get_match_count(source_id, Identifier("maps", "map_liths"))

    lith_count = db.run_query(
        """SELECT count(*) FROM maps.legend_liths sn
        JOIN maps.legend p ON p.legend_id = sn.legend_id
        WHERE p.source_id = :source_id""",
        {"source_id": source_id},
    ).scalar()
    return {"map_liths": map_liths_count, "legend_liths": lith_count}


class Liths(LegacyCommandBase):
    """
    macrostrat match liths <source_id>:
        Match a given map source to Macrostrat lithologies.
        Populates the table maps.legend_liths.
        Uses all available fields of matching, including lith, name, strat_name, descrip, and comments.

    Usage:
      macrostrat match liths <source_id>
      macrostrat match liths -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat match liths 123
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """

    source_id = None
    table = None
    field = None

    def do_work(self, field):
        try:
            self.pg["cursor"].execute(
                """
                INSERT INTO maps.legend_liths (legend_id, lith_id, basis_col)
                SELECT legend_id, liths.id, %(basis)s
                FROM maps.legend, macrostrat.liths
                WHERE source_id = %(source_id)s
                 AND (
                    legend.%(field)s ~* concat('\y', liths.lith, '\y')
                    OR
                    legend.%(field)s ~* concat('\y', liths.lith, 's', '\y')
                )
            """,
                {"source_id": self.source_id, "basis": field, "field": AsIs(field)},
            )
            self.pg["connection"].commit()
        except:
            pass

    def run(self, source_id):
        if source_id == "--help" or source_id == "-h":
            print(Liths.__doc__)
            sys.exit()

        start = time.time()
        Liths.source_id = source_id
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

        # Clean up
        self.pg["cursor"].execute(
            """
          DELETE FROM maps.legend_liths
          WHERE legend_id IN (
            SELECT legend_id
            FROM maps.legend
            WHERE source_id = %(source_id)s
          )
          AND basis_col NOT LIKE 'manual%%'
        """,
            {"source_id": source_id},
        )
        self.pg["connection"].commit()

        print("        + Done cleaning up")

        # Fields in burwell to match on
        fields = ["lith", "strat_name", "name", "descrip", "comments"]

        # Filter null fields
        self.pg["cursor"].execute(
            """
        SELECT
            count(distinct lith)::int AS lith,
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
        for field in fields:
            Liths.do_work(self, field)
