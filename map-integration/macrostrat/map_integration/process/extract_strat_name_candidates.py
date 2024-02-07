"""
This is a new command in Version 2, created Feb 2024. It is used
to extract stratigraphic name candidates from map source polygon tables, using
a combination of spatial and string matching against the Macrostrat database.
It would ideally be done in a sources.*_polygons table, but can also be applied
directly to the maps schema.
"""
from pathlib import Path

from psycopg2.sql import SQL, Identifier
from typer import Option

from ..database import db
from ..utils import MapInfo

__here__ = Path(__file__).parent


def extract_strat_name_candidates(
    map: MapInfo,
    field: str = Option(
        None,
        help="The field to extract from. Defaults to a concatenation of all text fields.",
    ),
):
    """
    Extract stratigraphic name candidates from a given map source's polygon table.
    Populates the strat_name field in the maps.sources table.
    When there are multiple strat names, they should be separated by a semicolon.
    """

    poly_table = map.slug + "_polygons"

    if field is None:
        fields = get_all_fields(poly_table)
        # Coalesce all fields and cast to text
        fields = [field + "::text" for field in fields]
        fields = ", ".join(fields)
        field = f"concat_ws(' ', {fields})"

    proc = __here__ / "procedures" / "matched-strat-names.sql"

    res = db.run_query(
        proc,
        {
            "source_id": map.id,
            "match_table": Identifier("sources", poly_table),
            "match_field": SQL(field),
        },
    )

    for row in res:
        print(row)


def get_all_fields(poly_table: str):
    """
    Get all the text fields in a given polygon table.
    """
    column_names = db.run_query(
        """
        SELECT column_name
        FROM information_schema.columns WHERE table_name = :table
        AND table_schema = :schema
        WHERE data_type IN ('text', 'varchar', 'character varying', 'char')
          AND column_name != 'strat_name'
        """,
        {"table": poly_table, "schema": "sources"},
    ).scalars()

    return column_names
