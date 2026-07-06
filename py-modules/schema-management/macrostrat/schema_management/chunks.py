"""Explicit collection of Macrostrat's schema chunks.

This is the single, readable answer to "what is the database schema made of?".
Chunks are collected explicitly here rather than via decorator/import side
effects, so the full set and its dependency edges are visible in one place.

``schema/core`` is decomposed into named subsystem chunks so a ``target`` selects
a subsystem by name and builds its dependency closure. The decomposition is
deliberately conservative for now: ``public`` (foundational roles/schemas),
``macrostrat`` (the core relational model), and ``core`` (the catch-all
remainder — maps, storage, tiles, permissions, …). Finer subsystems (``maps``,
``tiles``, …) can be split out of ``core`` piecewise later; the dependency chain
preserves today's application order exactly.
"""

from pathlib import Path

from macrostrat.core.config import settings
from macrostrat.map_topology.config import TopologySchema

from .composer import SchemaDefinition

# Environments (defs.py vocabulary) in which the dev-only layers apply. Mirrors
# ``schema_dirs_for_environment`` and the topology gate in defs.py.
_DEV_ENVS = frozenset({"development", "local"})

# Foundational files (roles, globals, public schema), applied before everything.
_PUBLIC_FILES = ["0000-globals.sql", "0000-roles.sql", "0001-public.sql"]
# The macrostrat relational model.
_MACROSTRAT_DIR = "0002-macrostrat"


def _core_dir() -> Path:
    return settings.srcroot / "schema" / "core"


def _core_remainder() -> list[Path]:
    """Top-level ``schema/core`` entries not owned by ``public`` or ``macrostrat``.

    Computed (rather than hand-listed) so new files land in ``core`` by default
    until they are explicitly extracted into their own subsystem chunk.
    """
    owned = set(_PUBLIC_FILES) | {_MACROSTRAT_DIR}
    return [p for p in sorted(_core_dir().iterdir()) if p.name not in owned]


def all_chunks() -> list[SchemaDefinition]:
    """Every schema chunk, independent of environment."""
    core = _core_dir()
    schema_dir = settings.srcroot / "schema"
    return [
        SchemaDefinition(
            name="public",
            provides=[core / f for f in _PUBLIC_FILES],
        ),
        SchemaDefinition(
            name="macrostrat",
            depends_on=["public"],
            provides=[core / _MACROSTRAT_DIR],
        ),
        SchemaDefinition(
            name="core",
            depends_on=["macrostrat"],
            provides=_core_remainder(),
        ),
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
