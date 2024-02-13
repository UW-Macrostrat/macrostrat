"""
This is a new command in Version 2, created Feb 2024. It is used
to extract stratigraphic name candidates from map source polygon tables, using
a combination of spatial and string matching against the Macrostrat database.
It would ideally be done in a sources.*_polygons table, but can also be applied
directly to the maps schema.
"""
from collections import defaultdict
from pathlib import Path

from psycopg2.sql import SQL, Identifier
from rich import print
from typer import Option

from ..database import db, sql_file
from ..utils import MapInfo

__here__ = Path(__file__).parent


def extract_strat_name_candidates(
    map: MapInfo,
    field: str = Option(
        "name",
        help="The field to extract from. Defaults to a concatenation of all text fields.",
    ),
    all_fields: bool = False,
    overwrite: bool = False,
):
    """
    Extract stratigraphic name candidates from a given map source's polygon table.
    Populates the strat_name field in the maps.sources table.
    When there are multiple strat names, they should be separated by a semicolon.
    """

    poly_table = map.slug + "_polygons"

    if all_fields:
        fields = get_all_fields(poly_table)
        # Coalesce all fields and cast to text
        fields = [f'"{field}"::text' for field in fields]
        fields = ", ".join(fields)
        field = f"concat_ws(' ', {fields})"

    proc = sql_file("matched-strat-names")

    table = Identifier("sources", poly_table)
    field = SQL(field)

    params = {
        "match_table": table,
        "match_field": field,
    }

    res = db.run_query(
        proc,
        {
            "source_id": map.id,
            "id_field": Identifier("_pkid"),
            **params,
        },
    )

    index = defaultdict(list)

    for row in res:
        if row.rank_name is not None and row.match_text is not None:
            index[row.match_text].append(row.rank_name)

    where_clause = SQL("strat_name IS NULL")
    if overwrite:
        where_clause = SQL("TRUE")

    for match_text, rank_names in index.items():
        if len(rank_names) > 3:
            continue
        rank_names = "; ".join(rank_names)
        print("[dim]" + match_text)
        print(rank_names)
        print()
        db.run_sql(
            """
            UPDATE {match_table}
            SET strat_name = :rank_names
            WHERE {match_field} = :match_text
              AND {where_clause}
            """,
            {
                **params,
                "match_text": match_text,
                "rank_names": rank_names,
                "where_clause": where_clause,
            },
        )


def get_all_fields(poly_table: str):
    """
    Get all the text fields in a given polygon table.
    """
    column_names = db.run_query(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :table
          AND table_schema = :schema
          AND data_type IN ('text', 'varchar', 'character varying', 'char')
          AND column_name != 'strat_name'
        """,
        {"table": poly_table, "schema": "sources"},
    ).scalars()

    return column_names
