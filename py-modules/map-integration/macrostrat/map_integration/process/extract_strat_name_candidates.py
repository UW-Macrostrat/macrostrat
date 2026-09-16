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

    # Keyed by the text the names were found in: that is what the update below
    # matches rows on, and several names found in one text become one
    # semicolon-separated value.
    index = defaultdict(list)

    for row in res:
        if row.rank_name is not None and row.match_text is not None:
            index[row.match_text].append(row.rank_name)

    candidates = {
        match_text: "; ".join(rank_names)
        for match_text, rank_names in index.items()
        # More than three candidates for one unit is a sign the match is noise
        # rather than a name.
        if len(rank_names) <= 3
    }

    for match_text, rank_names in candidates.items():
        # Truncated: `match_text` is every text column concatenated, and a unit
        # with a full `descrip` runs to thousands of characters.
        summary = " ".join(match_text.split())
        if len(summary) > 100:
            summary = summary[:100] + "..."
        print(f"[dim]{summary}[/]\n{rank_names}\n")

    if not candidates:
        print("[dim]No strat name candidates found")
        return

    apply_candidates(db, map, candidates, params, schema=schema, overwrite=overwrite)


def apply_candidates(
    db, map: MapInfo, candidates: dict[str, str], params, schema: str, overwrite: bool
):
    """Write the candidates back in a single pass over the table.

    One `UPDATE` per candidate would match on `{match_field}` -- usually a
    `concat_ws` over every text column, so no index can serve it -- and scan the
    source's rows once per distinct text. That is 9,028 scans of 216,462 rows on
    a map like Alaska. Staging the candidates and joining on a hash of the same
    expression does it in one.
    """
    db.run_sql(
        """
        DROP TABLE IF EXISTS strat_name_candidates;
        CREATE TEMPORARY TABLE strat_name_candidates (
          match_md5 text PRIMARY KEY,
          rank_names text NOT NULL
        );
        """
    )
    db.run_sql(
        "INSERT INTO strat_name_candidates VALUES (md5(:match_text), :rank_names)",
        [
            {"match_text": match_text, "rank_names": rank_names}
            for match_text, rank_names in candidates.items()
        ],
    )

    where_clauses = ["md5({match_field}) = c.match_md5"]
    if schema != "sources":
        where_clauses.append("source_id = :source_id")
    if not overwrite:
        where_clauses.append("strat_name IS NULL")

    db.run_sql(
        """
        UPDATE {match_table}
        SET strat_name = c.rank_names
        FROM strat_name_candidates c
        WHERE """
        + " AND ".join(where_clauses),
        {**params, "source_id": map.id},
    )
    db.run_sql("DROP TABLE IF EXISTS strat_name_candidates")


#: Text columns that identify a feature rather than describe it. Including one
#: makes every row's concatenated text unique -- on one NGS quadrangle that is
#: 6,317 distinct texts instead of 53 -- which defeats the deduplication the
#: match query depends on, and feeds meaningless tokens to the word matcher.
IDENTIFIER_COLUMNS = ("strat_name", "orig_id")


def get_all_fields(db, schema: str, table: str):
    """
    Get all the descriptive text fields in a given polygon table.
    """
    column_names = db.run_query(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :table
          AND table_schema = :schema
          AND data_type IN ('text', 'varchar', 'character varying', 'char')
          AND column_name != ALL(:excluded)
        ORDER BY ordinal_position
        """,
        {"table": table, "schema": schema, "excluded": list(IDENTIFIER_COLUMNS)},
    ).scalars()

    return column_names
