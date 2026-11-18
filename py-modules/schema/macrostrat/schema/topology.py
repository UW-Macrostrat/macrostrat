"""What PostGIS topology needs from schema inspection and diffing."""

from sqlalchemy.dialects.postgresql.base import ischema_names
from sqlalchemy.types import UserDefinedType


class TopoGeometry(UserDefinedType):
    """PostGIS `topogeometry`, which SQLAlchemy's Postgres dialect doesn't know.

    Unregistered, reflection warns per column on every migration check that
    touches `map_bounds`.
    """

    cache_ok = True

    def get_col_spec(self, **kw):
        return "topogeometry"


ischema_names["topogeometry"] = TopoGeometry


def filter_topology_changes(changes):
    """Drop topology objects from a diff: they embed a per-database topology id.

    A planning database builds its topology from scratch, so `CreateTopology`
    assigns id 1 there while a long-lived database is on some other id. Anything
    that embeds that id looks like a difference on every diff, and "fixing" it
    writes the planning database's id into the live one.
    """
    for inspector in (changes.i_from, changes.i_target):
        inspector.constraints = {
            k: v
            for k, v in inspector.constraints.items()
            if not v.name.startswith("check_topogeom_")
        }
        inspector.sequences = {
            k: v
            for k, v in inspector.sequences.items()
            if not v.name.startswith("topogeo_s_")
        }
        # The topology id is a literal in this trigger's arguments; rewritten,
        # every topogeometry insert fails with `Layer N does not exist`.
        inspector.triggers = {
            k: v
            for k, v in inspector.triggers.items()
            if v.name != "relation_integrity_checks"
        }
