"""Repair topology metadata that a dump/restore renumbered."""

from macrostrat.database import Database
from macrostrat.schema_management import Migration

TOPOLOGY = "map_bounds_topology"

#: True when the `relation_integrity_checks` trigger disagrees with the topology
#: id in `topology.topology`, or a layer's check constraint is missing/unvalidated.
_DRIFT = """
SELECT
  EXISTS (
    SELECT 1 FROM topology.topology t
    JOIN pg_trigger g
      ON g.tgname = 'relation_integrity_checks'
     AND g.tgrelid = (t.name || '.relation')::regclass
    WHERE t.name = :name
      AND pg_get_triggerdef(g.oid) NOT LIKE
          '%relationtrigger(' || quote_literal(t.id::text) || '%'
  )
  OR EXISTS (
    SELECT 1 FROM topology.layer l
    JOIN topology.topology t ON t.id = l.topology_id
    LEFT JOIN pg_constraint c
      ON c.conname = 'check_topogeom_topo'
     AND c.conrelid = (l.schema_name || '.' || l.table_name)::regclass
    WHERE t.name = :name
      AND (c.oid IS NULL OR NOT c.convalidated)
  )
"""


class RelationTriggerRepair(Migration):
    """Re-point the topology relation trigger and layer constraints.

    PostGIS records the topology id in places a restore can renumber: the
    per-layer `check_topogeom_topo` constraints, and the
    `relation_integrity_checks` trigger, which holds the id as a *literal* while
    `topology.topology.id` comes from a sequence. When those disagree, every
    topogeometry insert fails with `Layer N does not exist in topology <stale
    id>` -- which breaks the whole topology update path while looking like a data
    problem.

    The repair itself lives in the topology-manager submodule, next to the
    constraint rebuild it belongs with; this only decides when to run it.
    """

    name = "map-bounds-relation-trigger-repair"
    subsystem = "maps"
    description = "Repair topology relation trigger and layer constraints"
    readiness_state = "ga"
    destructive = False

    # The mismatch is a value rather than a schema shape, so both conditions
    # test live catalog state.
    preconditions = [lambda db: _has_drift(db)]
    postconditions = [lambda db: not _has_drift(db)]

    def apply(self, database: Database):
        # Imported here, not at module scope: `config` imports this package to
        # register its migrations, so a top-level import would be circular.
        from ..config import get_topo_manager

        get_topo_manager().rebuild_layer_constraints()


def _has_drift(db: Database) -> bool:
    return db.run_query(_DRIFT, dict(name=TOPOLOGY)).scalar() is True
