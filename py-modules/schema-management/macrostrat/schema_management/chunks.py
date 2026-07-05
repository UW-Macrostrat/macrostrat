"""Explicit collection of Macrostrat's schema chunks.

This is the single, readable answer to "what is the database schema made of?".
Chunks are collected explicitly here rather than via decorator/import side
effects, so the full set and its dependency edges are visible in one place.

For now this maps the *existing* on-disk layout — the ``schema/core``,
``schema/development`` and ``schema/local`` directories plus the topology
fixtures — onto chunks **without moving any files**. Relocating SQL into owning
modules is a later step, unblocked once the composer is verified as a no-op.
"""

from macrostrat.core.config import settings
from macrostrat.map_topology.config import TopologySchema

from .composer import SchemaDefinition

# Environments (defs.py vocabulary) in which the dev-only layers apply. Mirrors
# ``schema_dirs_for_environment`` and the topology gate in defs.py.
_DEV_ENVS = frozenset({"development", "local"})


def all_chunks() -> list[SchemaDefinition]:
    """Every schema chunk, independent of environment."""
    schema_dir = settings.srcroot / "schema"
    return [
        SchemaDefinition(name="core", provides=[schema_dir / "core"]),
        SchemaDefinition(
            name="development",
            depends_on=["core"],
            provides=[schema_dir / "development"],
            environments=_DEV_ENVS,
        ),
        SchemaDefinition(
            name="local",
            depends_on=["development"],
            provides=[schema_dir / "local"],
            environments=frozenset({"local"}),
        ),
        TopologySchema,
    ]


def chunks_for_environment(env: str) -> list[SchemaDefinition]:
    """The chunks that apply in the given environment."""
    return [c for c in all_chunks() if c.applies_to(env)]
