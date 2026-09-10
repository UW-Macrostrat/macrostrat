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

from ..database import get_database, sql_file
from ..utils import MapInfo

__here__ = Path(__file__).parent


def extract_strat_name_candidates(
    map: MapInfo,
    field: str | None = None,
    overwrite: bool = False,
    use_sources: bool = False,
):
    """
    Extract stratigraphic name candidates from a given map source's polygon table.
    Populates the strat_name field in the maps.sources table.
    When there are multiple strat names, they should be separated by a semicolon.
    """
    db = get_database()

    schema = "maps"
    table = "polygons"
    if use_sources:
        schema = "sources"
        table = db.run_query(
            "SELECT primary_table FROM maps.sources WHERE slug = :slug",
            {"slug": map.slug},
        ).scalar()
        if table is None:
            raise Exception("No polygon table found")

    extract_strat_names_for_table(
        db, map, table, field=field, overwrite=overwrite, schema=schema
    )


def extract_strat_names_for_table(
    db,
    map: MapInfo,
    table: str,
    field: str | None = None,
    overwrite: bool = False,
    schema: str = "sources",
):
    if field is None:
        fields = get_all_fields(db, schema, table)
        # Coalesce all fields and cast to text
        fields = [f'"{field}"::text' for field in fields]
        fields = ", ".join(fields)
        field = f"concat_ws(' ', {fields})"

    proc = sql_file("matched-strat-names")

    table = Identifier(schema, table)
    field = SQL(field)

    params = {
        "match_table": table,
        "match_field": field,
    }

    id_field = Identifier("map_id")
    if schema == "sources":
        id_field = Identifier("_pkid")

    res = db.run_query(
        proc,
        {
            "source_id": map.id,
            "id_field": id_field,
            **params,
        },
    )

    index = defaultdict(list)

    for row in res:
        if row.rank_name is not None and row.strat_name is not None:
            index[row.strat_name].append(row.rank_name)

    where_clauses = [
        "{match_field} = :match_text",
    ]

    if schema != "sources":
        where_clauses.append("source_id = :source_id")
    if not overwrite:
        where_clauses.append("strat_name IS NULL")

    query = """
            UPDATE {match_table}
            SET strat_name = :rank_names
            WHERE
            """ + where_clauses.join(" AND ")

    for match_text, rank_names in index.items():
        if len(rank_names) > 3:
            continue
        rank_names = "; ".join(rank_names)
        print("[dim]" + match_text)
        print(rank_names)
        print()
        db.run_sql(
            query,
            {
                **params,
                "match_text": match_text,
                "rank_names": rank_names,
                "source_id": map.id,
            },
        )


def get_all_fields(db, schema: str, table: str):
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
        {"table": table, "schema": schema},
    ).scalars()

    return column_names
