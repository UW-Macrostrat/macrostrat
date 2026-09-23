import time

from psycopg2.sql import Identifier
from rich import print

from macrostrat.core.exc import MacrostratError
from macrostrat.database import Database

from ..utils import MapInfo
from .utils import find_scale_table, get_match_count, populated_fields

#: Legend fields to match lithologies against, in the order they are tried.
MATCH_FIELDS = ["lith", "strat_name", "name", "descrip", "comments"]


def match_liths(db: Database, map_info: MapInfo):
    """Rebuild `maps.legend_liths` for one source from its legend text."""
    start = time.time()
    source_id = map_info.id

    exists = db.run_query(
        "SELECT source_id FROM maps.sources WHERE source_id = :source_id",
        {"source_id": source_id},
    ).first()
    if exists is None:
        raise MacrostratError(f"Source {source_id} was not found in maps.sources")

    scale = find_scale_table(db, source_id)

    fields = matchable_fields(db, source_id, scale)

    # One transaction for the whole rebuild, so the table is never seen
    # half-matched. `db.transaction()` opens its *own* connection and rebinds
    # `db.session` to it, so the staging table has to be created inside -- one
    # made outside is on a different connection and invisible here.
    with db.transaction():
        stage_matches(db)
        for field in fields:
            match_field(db, source_id, field)
        added, removed = merge_matches(db, source_id)

    print(
        f"        + Matched in {time.time() - start:.1f}s"
        f" ([green]+{added}[/] [red]-{removed}[/])"
    )

    counts = get_lith_count(db, map_info.id)
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


def stage_matches(db):
    """Start a staging table for this source's matches.

    `ON COMMIT DROP` is load-bearing. `db.transaction()` takes its connection
    from the pool, and a pooled connection keeps its temporary tables when it is
    handed back -- so in a sweep the next source was given a connection that
    still had this table on it, and the `CREATE` failed with "already exists",
    aborting that source's whole rebuild. Scoping the table to the transaction
    ends it with the transaction rather than with the connection.
    """
    db.run_sql(
        """
        CREATE TEMPORARY TABLE legend_lith_matches (
          legend_id integer NOT NULL,
          lith_id integer NOT NULL,
          basis_col text NOT NULL
        ) ON COMMIT DROP
        """
    )


def merge_matches(db, source_id: int) -> tuple[int, int]:
    """Bring `maps.legend_liths` into line with what was staged.

    **A merge, not a rebuild.** The old workflow deleted every automatic match
    for the source and then re-inserted, which had two problems. The delete ran
    in its own transaction -- `run_sql` gives each statement one when the session
    is not already in a transaction -- so between it and the last insert the
    source had no lithologies at all, and a field that failed midway left it
    that way. And since matching is re-run whenever the lexicon or the
    descriptions change, every unchanged row was churned for nothing.

    `(legend_id, lith_id, basis_col)` is the whole row and carries a UNIQUE
    constraint, so there is no payload to update: a row either belongs or does
    not. The merge inserts what is new, leaves what is unchanged untouched, and
    removes what the staged set no longer contains. Manual matches are outside
    it entirely.

    Runs inside the caller's transaction; see `match_liths`.
    """
    added = db.run_query(
        """
        INSERT INTO maps.legend_liths (legend_id, lith_id, basis_col)
        SELECT DISTINCT legend_id, lith_id, basis_col
        FROM legend_lith_matches
        ON CONFLICT (legend_id, lith_id, basis_col) DO NOTHING
        """,
        {},
    ).rowcount
    removed = db.run_query(
        """
        DELETE FROM maps.legend_liths ll
        USING maps.legend l
        WHERE ll.legend_id = l.legend_id
          AND l.source_id = :source_id
          AND ll.basis_col NOT LIKE 'manual%'
          AND NOT EXISTS (
            SELECT 1 FROM legend_lith_matches m
            WHERE m.legend_id = ll.legend_id
              AND m.lith_id = ll.lith_id
              AND m.basis_col = ll.basis_col
          )
        """,
        {"source_id": source_id},
    ).rowcount
    return added, removed


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
        # A savepoint, because this runs inside the rebuild's transaction: a
        # failing statement would otherwise abort the whole rebuild rather than
        # just this field.
        with db.savepoint():
            db.run_sql(
                r"""
            INSERT INTO legend_lith_matches (legend_id, lith_id, basis_col)
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
