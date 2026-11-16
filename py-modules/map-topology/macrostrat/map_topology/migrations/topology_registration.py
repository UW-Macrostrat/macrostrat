"""Register a topology whose tables exist without PostGIS knowing about them."""

from psycopg2.sql import Identifier

from macrostrat.database import Database
from macrostrat.schema_management import Migration, exists

TOPOLOGY = "map_bounds_topology"
_SCHEMAS = ("map_bounds", TOPOLOGY)

_REGISTERED = "SELECT EXISTS (SELECT 1 FROM topology.topology WHERE name = :name)"

_UNREGISTERED_COLUMNS = """
SELECT n.nspname AS schema_name, c.relname AS table_name, a.attname AS column_name
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE a.atttypid = to_regtype('topology.topogeometry')
  AND NOT a.attisdropped
  AND c.relkind = 'r'
  AND n.nspname = ANY(:schemas)
  AND NOT EXISTS (
    SELECT 1 FROM topology.layer l
    WHERE l.schema_name = n.nspname
      AND l.table_name = c.relname
      AND l.feature_column = a.attname
  )
"""

_HAS_PRIMITIVES = """
SELECT EXISTS (SELECT 1 FROM {topology}.edge_data)
    OR EXISTS (SELECT 1 FROM {topology}.node)
    OR EXISTS (SELECT 1 FROM {topology}.face WHERE face_id > 0)
"""


def _registered(db: Database) -> bool:
    return db.run_query(_REGISTERED, dict(name=TOPOLOGY)).scalar()


def _unregistered_columns(db: Database) -> list:
    return db.run_query(_UNREGISTERED_COLUMNS, dict(schemas=list(_SCHEMAS))).all()


def _fully_registered(db: Database) -> bool:
    """The topology and each of its topogeometry columns are known to PostGIS."""
    return _registered(db) and not _unregistered_columns(db)


def _safe_to_rebuild(db: Database) -> bool:
    """Registered already, or its schema holds no edges, nodes or faces to lose."""
    if _registered(db):
        return True
    schema = db.run_query("SELECT to_regnamespace(:name)", dict(name=TOPOLOGY))
    if schema.scalar() is None:
        return True
    params = dict(topology=Identifier(TOPOLOGY))
    return not db.run_query(_HAS_PRIMITIVES, params).scalar()


class TopologyRegistration(Migration):
    """Recreate the topology when its tables exist without its registration.

    `schema plan` diffs the topology schema's tables but not the
    `topology.topology` and `topology.layer` rows that make them a topology, so
    a database the plan built them in has a schema PostGIS cannot find, and
    `CreateTopology` refuses to run over it.
    """

    name = "map-bounds-topology-registration"
    owner = None  # `CreateTopology` writes PostGIS's own catalog
    subsystem = "maps"
    description = "Register the map-bounds topology and its topogeometry columns"
    readiness_state = "ga"
    # Drops the unregistered shell schema and unreadable topogeometry columns
    destructive = True

    preconditions = [exists("map_bounds", "map_area"), _safe_to_rebuild]
    postconditions = [_fully_registered]

    def apply(self, database: Database):
        # Imported here: `config` imports this package to register its migrations
        from ..config import create_topo_fixtures

        if not _registered(database):
            database.run_sql(
                "DROP SCHEMA IF EXISTS {schema} CASCADE",
                params=dict(schema=Identifier(TOPOLOGY)),
                raise_errors=True,
            )
        # Cascades to views over the column (`map_area_sync`); the fixtures recreate them
        for col in _unregistered_columns(database):
            database.run_sql(
                "ALTER TABLE {table} DROP COLUMN {column} CASCADE",
                params=dict(
                    table=Identifier(col.schema_name, col.table_name),
                    column=Identifier(col.column_name),
                ),
                raise_errors=True,
            )
        database.session.commit()
        create_topo_fixtures(database)
