"""Migrations for the map-topology subsystem.

Housed with the code they touch rather than in the central `schema/_migrations`
tree. Discovery is by `Migration.__subclasses__()`, so a migration is registered
simply by being imported -- which is what the imports below are for. `config.py`
imports this package alongside the `TopologySchema` definition, so any CLI
invocation that loads the subsystem also registers its migrations.

Each migration gets its own directory: `Migration.apply` runs *every* `.sql`
file next to the class, so sharing a directory would run unrelated migrations.
"""

from . import (  # noqa: F401
    carto_v1_compilation,
    compilation_assembly_mode,
    map_priority_columns,
    map_topo_pieces,
    relation_trigger_repair,
    source_id_rename,
)

__all__ = [
    "carto_v1_compilation",
    "source_id_rename",
    "relation_trigger_repair",
    "map_topo_pieces",
    "compilation_assembly_mode",
    "map_priority_columns",
]
