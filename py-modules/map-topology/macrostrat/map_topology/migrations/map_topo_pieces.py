"""Pieces stop being topogeometries; compilations stop having them."""

from macrostrat.database import Database
from macrostrat.schema_management import Migration, _any


def _layer_exists(table: str, column: str):
    def check(db: Database) -> bool:
        return (
            db.run_query(
                """
                SELECT EXISTS (
                  SELECT 1 FROM topology.layer
                  WHERE schema_name = 'map_bounds'
                    AND table_name = :table
                    AND feature_column = :column
                )
                """,
                dict(table=table, column=column),
            ).scalar()
            is True
        )

    return check


class MapTopoPiecesMigration(Migration):
    """Drop the `map_topo.topo` and `map_area.composite_topo` topogeometry layers.

    A map's bounds are noded piece by piece into its single `map_area.topo`
    (the topology library's accumulating `update_boundary_topo`), so a piece is a
    record -- geometry, status, error -- and not a topogeometry: the layer held a
    second reference to every primitive the map's own topogeometry already listed,
    a third of `relation`. A compilation has no topogeometry at all: its bounds
    come from the `compile` opening operation and identity resolves a materialized
    one through its members, so the hierarchical `composite_topo` layer goes too.

    `DropTopoGeometryColumn` cannot travel through a schema diff, which is why
    this is a migration; the columns and functions around the layers are declared
    away in the fixtures.
    """

    name = "map-topo-pieces"
    subsystem = "maps"
    description = "Drop the map_topo and composite_topo topogeometry layers"
    readiness_state = "ga"
    destructive = True

    preconditions = [
        _any(
            [
                _layer_exists("map_topo", "topo"),
                _layer_exists("map_area", "composite_topo"),
            ]
        )
    ]
    postconditions = [
        lambda db: not _layer_exists("map_topo", "topo")(db),
        lambda db: not _layer_exists("map_area", "composite_topo")(db),
    ]

    def apply(self, database: Database):
        for table, column in (("map_topo", "topo"), ("map_area", "composite_topo")):
            if _layer_exists(table, column)(database):
                database.run_sql(
                    "SELECT topology.DropTopoGeometryColumn('map_bounds', :table, :column)",
                    dict(table=table, column=column),
                    raise_errors=True,
                )
