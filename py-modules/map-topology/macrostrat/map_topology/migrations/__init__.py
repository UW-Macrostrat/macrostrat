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
    compilation_multiscale,
    layer_bounds,
    layers_by_compilation,
    map_area_from_rgeom,
    map_priority_columns,
    map_topo_adopt,
    map_topo_pieces,
    relation_trigger_repair,
    source_id_rename,
    topology_registration,
)

__all__ = [
    "carto_v1_compilation",
    "layers_by_compilation",
    "map_area_from_rgeom",
    "source_id_rename",
    "relation_trigger_repair",
    "topology_registration",
    "map_topo_pieces",
    "map_topo_adopt",
    "layer_bounds",
    "compilation_assembly_mode",
    "compilation_multiscale",
    "map_priority_columns",
]
