from typing import Annotated, Optional

from psycopg.sql import SQL, Identifier
from typer import Option

from ..database import get_database
from ..utils import MapInfo

# `ST_MakeValid` repairs a self-intersection by *decomposing* the geometry, and
# what comes back is frequently a `GeometryCollection`: the repaired area plus
# zero-area debris where the ring crossed itself. A staging table's geometry
# column is typed, so that collection cannot be stored -- hence the extraction of
# just the dimension the column holds. This is the same idiom
# `map_topology.bounds.build.recompute_union` already uses.
#
# It is lossy in principle and not in practice: the discarded components are
# slivers. On NGS's two invalid Alaska polygons -- ring self-intersections at the
# antimeridian -- extraction keeps 100.000000% of the area.
REPAIR = {
    "polygons": "ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))",
    "lines": "ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 2))",
    # A point is never invalid, so the filter below never selects one. Kept for
    # symmetry; `ST_MakeValid` of a point is that point, and the column is
    # single-typed so nothing may be wrapped in `ST_Multi`.
    "points": "ST_MakeValid(geom)",
}


def fix_geometries(
    db,
    map: MapInfo,
    *,
    staging_prefix: str = None,
):
    """Repair invalid geometries in a map's staging tables.

    `staging_prefix` names the `sources.<prefix>_{polygons,lines,points}` triple
    and defaults to the map's slug -- the same argument `copy_to_maps` takes, and
    for the same reason: a compilation whose members share one staging table has
    no `sources.<slug>_polygons` of its own.

    Only invalid rows are rewritten. `ST_MakeValid` of a valid geometry returns
    it unchanged, so the filter changes no outcome -- but without it a map like
    NGS's Alaska member rewrites 216,462 geometries to repair two.
    """
    prefix = staging_prefix or map.slug
    for table, repair in REPAIR.items():
        ident = Identifier("sources", f"{prefix}_{table}")
        db.run_sql(
            "UPDATE {table} SET geom = {repair}"
            " WHERE source_id = :source_id AND NOT ST_IsValid(geom)",
            {"source_id": map.id, "table": ident, "repair": SQL(repair)},
        )


def fix_geometries_command(
    map: MapInfo,
    staging_prefix: Annotated[
        Optional[str],
        Option(
            "--staging-prefix",
            help="Name the sources.<prefix>_* staging tables (default: the slug)",
        ),
    ] = None,
):
    """Fix geometries in a map source."""
    fix_geometries(get_database(), map, staging_prefix=staging_prefix)
