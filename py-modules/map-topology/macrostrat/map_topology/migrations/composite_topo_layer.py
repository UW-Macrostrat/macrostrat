"""Add the hierarchical layer that holds compilation boundaries."""

from macrostrat.database import Database
from macrostrat.schema_management import Migration

TOPOLOGY = "map_bounds_topology"

_LAYER_EXISTS = """
SELECT EXISTS (
  SELECT 1 FROM topology.layer
  WHERE schema_name = 'map_bounds'
    AND table_name = 'map_area'
    AND feature_column = 'composite_topo'
)
"""


class CompositeTopoLayer(Migration):
    """Create `map_area.composite_topo`, the level-1 layer compilations live in.

    A topogeometry column cannot arrive through a schema diff: the planner
    filters topology elements out entirely, because they embed the
    `topology.topology` id and a planning database numbers it differently. So
    `AddTopoGeometryColumn` has to run here, even though it reads more naturally
    beside the rest of the compilation schema -- where it stays, for the
    build-from-zero path that `create_tables` follows.
    """

    name = "map-bounds-composite-topo-layer"
    subsystem = "maps"
    description = "Add the hierarchical layer holding compilation boundaries"
    readiness_state = "ga"
    destructive = False

    preconditions = [lambda db: not _layer_exists(db)]
    postconditions = [lambda db: _layer_exists(db)]

    def apply(self, database: Database):
        database.run_sql(
            """
            SELECT topology.AddTopoGeometryColumn(
              :topology,
              'map_bounds',
              'map_area',
              'composite_topo',
              'POLYGON',
              (
                SELECT layer_id FROM topology.layer
                WHERE schema_name = 'map_bounds'
                  AND table_name = 'map_area'
                  AND feature_column = 'topo'
              )
            )
            """,
            dict(topology=TOPOLOGY),
        )


def _layer_exists(db: Database) -> bool:
    return db.run_query(_LAYER_EXISTS).scalar() is True
