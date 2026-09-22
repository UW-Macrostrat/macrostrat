import time

from psycopg2.sql import Identifier
from rich import print

from macrostrat.core.exc import MacrostratError

from ..database import get_database
from ..utils import MapInfo
from .utils import find_scale_table, get_match_count, populated_fields

#: Legend fields to match lithologies against, in the order they are tried.
MATCH_FIELDS = ["lith", "strat_name", "name", "descrip", "comments"]


def match_liths(map: MapInfo):
    """
    Match a given map source to Macrostrat lithologies.
    Populates the table maps.legend_liths.
    Uses all available fields of matching, including lith, name, strat_name, descrip, and comments.
    """
    db = get_database()
    run_lith_match(db, map.id)

    counts = get_lith_count(db, map.id)
    mlc = counts["map_liths"]
    llc = counts["legend_liths"]
    print(f"Matched [bold cyan]{llc}[/] legend liths ([bold cyan]{mlc}[/] map liths)")


def get_lith_count(db, source_id: int):
    map_liths_count = get_match_count(db, source_id, Identifier("maps", "map_liths"))

    lith_count = db.run_query(
        """SELECT count(*) FROM maps.legend_liths sn
        JOIN maps.legend p ON p.legend_id = sn.legend_id
        WHERE p.source_id = :source_id""",
        {"source_id": source_id},
    ).scalar()
    return {"map_liths": map_liths_count, "legend_liths": lith_count}


def run_lith_match(db, source_id: int):
    """Rebuild `maps.legend_liths` for one source from its legend text."""
    start = time.time()

    exists = db.run_query(
        "SELECT source_id FROM maps.sources WHERE source_id = :source_id",
        {"source_id": source_id},
    ).first()
    if exists is None:
        raise MacrostratError(f"Source {source_id} was not found in maps.sources")

    scale = find_scale_table(db, source_id)

    clear_matches(db, source_id)
    print("        + Done cleaning up")

    for field in matchable_fields(db, source_id, scale):
        match_field(db, source_id, field)

    print(f"        + Matched in {time.time() - start:.1f}s")


def clear_matches(db, source_id: int):
    """Drop this source's automatic matches, keeping anything matched by hand."""
    db.run_sql(
        """
        DELETE FROM maps.legend_liths
        WHERE legend_id IN (
          SELECT legend_id FROM maps.legend WHERE source_id = :source_id
        )
        AND basis_col NOT LIKE 'manual%'
        """,
        {"source_id": source_id},
    )


def matchable_fields(db, source_id: int, scale: str) -> list[str]:
    """The subset of `MATCH_FIELDS` this source actually populates."""
    return populated_fields(db, source_id, scale, MATCH_FIELDS)


def match_field(db, source_id: int, field: str):
    r"""Match one legend field against `macrostrat.liths`.

    `\y` is a word boundary, so `lith` matches the word and not a substring of a
    longer one; the second branch is the plural.

    A failure here is reported and the remaining fields still run. The version-1
    command wrapped this in a bare `except: pass`, which made a field that could
    not match indistinguishable from one with nothing to match -- and there is a
    real difference worth seeing.
    """
    try:
        db.run_sql(
            r"""
            INSERT INTO maps.legend_liths (legend_id, lith_id, basis_col)
            SELECT legend_id, liths.id, :basis
            FROM maps.legend, macrostrat.liths
            WHERE source_id = :source_id
             AND (
                legend.{field} ~* concat('\y', liths.lith, '\y')
                OR
                legend.{field} ~* concat('\y', liths.lith, 's', '\y')
            )
            """,
            {"source_id": source_id, "basis": field, "field": Identifier(field)},
        )
    except Exception as err:  # noqa: BLE001 -- reported per field, see above
        print(f"        [yellow]+ {field} failed[/]: {str(err).splitlines()[0]}")
