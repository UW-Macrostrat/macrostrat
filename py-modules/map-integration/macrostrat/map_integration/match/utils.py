from psycopg2.sql import Identifier

from macrostrat.core.exc import MacrostratError

from ..database import get_database

#: Scale tables, coarsest first.
SCALES = ["tiny", "small", "medium", "large"]


def find_scale_table(db, source_id: int) -> str:
    """The scale table this source's polygons are in.

    `maps.sources.scale` already answers this, and is what `lookup.py` and
    `legend_lookup.py` read. It is checked rather than trusted, because it is
    authored metadata and the polygons are the fact -- but checking it is one
    query where probing every table in turn was up to four, twice per pipeline
    run, in two separate copies of this loop.
    """
    declared = db.run_query(
        "SELECT scale::text FROM maps.sources WHERE source_id = :source_id",
        {"source_id": source_id},
    ).scalar()

    candidates = SCALES
    if declared in SCALES:
        candidates = [declared] + [s for s in SCALES if s != declared]

    for scale in candidates:
        found = db.run_query(
            "SELECT map_id FROM {scale_table} WHERE source_id = :source_id LIMIT 1",
            {"scale_table": Identifier("maps", scale), "source_id": source_id},
        ).first()
        if found is not None:
            return scale

    raise MacrostratError(
        f"Source {source_id} is not present in any scale table",
        details=(
            "Copy it into the maps schema with `macrostrat maps process insert`"
            " and try again."
        ),
    )


def populated_fields(db, source_id: int, scale: str, fields: list[str]) -> list[str]:
    """Which of `fields` this source populates at all.

    `EXISTS` per column, not `count(distinct col)`. The question is "is this
    column entirely null", and counting distinct values sorts or hashes every row
    of the source to answer it; `EXISTS` stops at the first non-null. Five of
    those ran twice per pipeline run.
    """
    checks = ",\n".join(
        f"EXISTS (SELECT 1 FROM {{scale_table}} WHERE source_id = :source_id"
        f" AND {f} IS NOT NULL) AS {f}"
        for f in fields
    )
    row = db.run_query(
        f"SELECT {checks}",
        {"scale_table": Identifier("maps", scale), "source_id": source_id},
    ).one()

    populated = []
    for field in fields:
        if row._mapping[field]:
            populated.append(field)
        else:
            print(f"        + Excluding {field} because it is null")
    return populated


def get_match_count(db, source_id: int, table: Identifier):
    return db.run_query(
        """
        SELECT count(*) FROM {table} sn
        JOIN maps.polygons p ON p.map_id = sn.map_id
        WHERE p.source_id = :source_id;
        """,
        {"source_id": source_id, "table": table},
    ).scalar()
