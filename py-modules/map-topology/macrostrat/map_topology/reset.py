"""Rebuild the topology from nothing, keeping every map's bounds.

Everything in the topology schema is derived -- primitives, map faces, face
identities, edge relations -- so a topology whose labels went wrong can be
thrown away and re-noded from `map_area`, which holds the bounds themselves.
"""

from psycopg2.sql import Identifier

from macrostrat.database import Database

TOPOLOGY = "map_bounds_topology"

_UNREGISTER = """
DELETE FROM topology.layer
WHERE topology_id = (SELECT id FROM topology.topology WHERE name = :name);
DELETE FROM topology.topology WHERE name = :name;
"""

#: Topogeometry columns outside the topology schema, which goes whole.
_TOPOGEOMETRY_COLUMNS = """
SELECT n.nspname AS schema_name, c.relname AS table_name, a.attname AS column_name
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE a.atttypid = to_regtype('topology.topogeometry')
  AND NOT a.attisdropped
  AND c.relkind = 'r'
  AND n.nspname = 'map_bounds'
"""

#: Every map is noded again from its bounds: no pieces, nothing current.
_RESET_MAPS = """
DELETE FROM map_bounds.map_topo;
UPDATE map_bounds.map_area SET geometry_hash = NULL, topology_error = NULL;
"""


def reset_topology(db: Database):
    """Drop the topology and recreate it empty, ready to grid and re-node."""
    from .config import create_topo_fixtures
    from .grid import reset_grid_lines

    reset_grid_lines(db)
    db.run_sql(
        "DROP SCHEMA IF EXISTS {schema} CASCADE",
        params=dict(schema=Identifier(TOPOLOGY)),
        raise_errors=True,
    )
    # Cascades to views over the columns (`map_area_sync`); the fixtures recreate them
    for col in db.run_query(_TOPOGEOMETRY_COLUMNS).all():
        db.run_sql(
            "ALTER TABLE {table} DROP COLUMN {column} CASCADE",
            params=dict(
                table=Identifier(col.schema_name, col.table_name),
                column=Identifier(col.column_name),
            ),
            raise_errors=True,
        )
    # Last: PostGIS skips deleting a layer while a feature or relation row names it
    db.run_sql(_UNREGISTER, dict(name=TOPOLOGY), raise_errors=True)
    db.run_sql(_RESET_MAPS, raise_errors=True)
    db.session.commit()
    create_topo_fixtures(db)


def topology_is_empty(db: Database) -> bool:
    return not db.run_query(
        "SELECT EXISTS (SELECT 1 FROM map_bounds_topology.edge_data)"
    ).scalar()
