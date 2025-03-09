"""
Script to go along with maps-line-orientations migration,
to populate the sources.lines_oriented flag for some known maps.

  Date: 2025-03-07
"""

from macrostrat.core.database import get_database
from macrostrat.core.migrations import has_columns

_has_column = has_columns("maps", "sources", "lines_oriented")

db = get_database()

# This migration is only relevant if the lines_oriented column exists
assert _has_column(db)

# Legacy maps with consistently-oriented linework that needs to be reversed
valid_maps = [
    (229, "ab_spray"),
    (210, "bc_chinook"),
    (205, "bc_2017"),
    (154, "global2"),
    (75, "az_mohave"),
    (74, "az_peachsprings"),
    (40, "mt_trumbull"),
]

reversed_maps = [(4, "alberta")]

for _map in valid_maps + reversed_maps:
    args = dict(source_id=_map[0], slug=_map[1])
    needs_update = db.run_query(
        """
        SELECT lines_oriented IS NULL
        FROM maps.sources
        WHERE source_id = :source_id
          AND slug = :slug
        """,
        args,
    ).scalar()
    if needs_update is None:
        print(f"Map {_map} not found in database")
        continue
    elif not needs_update:
        print(f"Map {_map} already has lines_oriented set")
        continue

    if _map in reversed_maps:
        db.run_sql(
            """
            UPDATE maps.lines SET geom = ST_Reverse(geom)
            WHERE source_id = :source_id
            """,
            dict(source_id=_map[0]),
        )

    db.run_sql(
        """
        UPDATE maps.sources SET lines_oriented = true
        WHERE source_id = :source_id
          AND slug = :slug
        """,
        args,
    )
