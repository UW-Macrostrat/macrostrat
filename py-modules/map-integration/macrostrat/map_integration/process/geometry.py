from psycopg.sql import SQL, Identifier
from rich import print

from ..database import sql_file
from ..utils import MapInfo, table_exists

_BOUNDARY_STATE = """
SELECT
  EXISTS (SELECT 1 FROM map_bounds.map_area WHERE id = :source_id) AS has_bounds,
  count(o.id) AS n_ops,
  count(o.id) FILTER (WHERE o.position > 0 OR o.operation <> 'union') AS n_composed
FROM map_bounds.boundary_op o
WHERE o.source_id = :source_id
"""

_SET_WEB_GEOM = """
UPDATE maps.sources s
SET web_geom = ST_Envelope(a.geometry)
FROM map_bounds.map_area a
WHERE a.id = s.source_id
  AND s.source_id = :source_id
"""


def create_bounds(db, source: MapInfo) -> bool:
    """Set a map's `map_area` boundary to the union of its features.

    Reads the map's polygons in `maps`, or its staging table when it has none
    there yet, so a staged map has bounds before it is inserted. Only a boundary
    this step wrote is replaced: one composed from operations belongs to
    `macrostrat bounds build`, and one with no operations pre-dates them.
    The web geometry is refreshed either way. Returns whether a boundary was written.
    """
    params = dict(source_id=source.id)
    state = db.run_query(_BOUNDARY_STATE, params).one()
    written = False

    if state.n_composed:
        print(
            f"[dim]{source.slug} has a boundary composed from {state.n_composed}"
            " operations; `macrostrat bounds build` maintains it[/]"
        )
    elif state.has_bounds and not state.n_ops:
        print(
            f"[dim]{source.slug} keeps a boundary that pre-dates boundary operations;"
            " `macrostrat bounds build --init` recomputes it[/]"
        )
    elif (features := _features(db, source)) is None:
        print(f"[yellow]{source.slug} has no polygons in `maps` or in staging[/]")
    else:
        db.run_sql(
            sql_file("seed-bounds"),
            dict(source_id=source.id, features=features),
            raise_errors=True,
        )
        print(f"[green]{source.slug}[/] boundary set from its polygons")
        written = True

    db.run_query(_SET_WEB_GEOM, params)
    db.session.commit()
    return written


def _features(db, source: MapInfo):
    """The map's polygons: in `maps` once inserted, else its staging table."""
    inserted = db.run_query(
        "SELECT EXISTS (SELECT 1 FROM maps.polygons WHERE source_id = :source_id)",
        dict(source_id=source.id),
    ).scalar()
    if inserted:
        return SQL("SELECT geom FROM maps.polygons WHERE source_id = :source_id")

    primary_table = db.run_query(
        "SELECT primary_table FROM maps.sources WHERE source_id = :source_id",
        dict(source_id=source.id),
    ).scalar()
    if primary_table is None or not table_exists(db, primary_table, schema="sources"):
        return None
    return SQL("SELECT geom FROM {} WHERE NOT coalesce(omit, false)").format(
        Identifier("sources", primary_table)
    )
