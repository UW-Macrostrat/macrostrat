"""Dependency-graph composer for Macrostrat's declarative schema.

This module assembles the database schema from a set of *chunks* ordered by a
declared dependency graph, rather than by the lexicographic filename ordering
used by :func:`apply_schema_for_environment`. Each chunk contributes one or more
*declarative providers* — either a directory of ``.sql`` files or a callable that
applies its own statements (e.g. the topology fixtures, which delegate to a
third-party library). Both provider kinds are idempotent and buildable from zero,
so they participate in the graph identically.

This is intentionally additive: it reproduces the existing build so it can be
verified as a no-op (see ``tests/test_schema_composer.py``) before any SQL is
relocated into owning modules.
"""

from graphlib import TopologicalSorter
from typing import Optional

from macrostrat.database import Database
from macrostrat.core import SchemaDefinition


def order_chunks(chunks: list[SchemaDefinition]) -> list[SchemaDefinition]:
    """Topologically sort chunks by ``depends_on``.

    Dependencies pointing outside the given set (e.g. env-filtered out) are
    tolerated: they order the graph but are skipped in the result.
    """
    databases = {c.database for c in chunks}
    if len(databases) != 1:
        raise ValueError(f"Chunks must all be in the same database, got {databases}")

    by_name = {c.name: c for c in chunks}
    graph = {c.name: c.depends_on for c in chunks}
    order = list(TopologicalSorter(graph).static_order())
    return [by_name[n] for n in order if n in by_name]


def build_schema(
    db: Database, env: str, chunks: Optional[list[SchemaDefinition]] = None
) -> Database:
    """Build the declarative schema for ``env`` by applying chunks in graph order."""
    if chunks is None:
        # Imported lazily to avoid a circular import at module load.
        from .chunks import chunks_for_environment

        chunks = chunks_for_environment(env)

    for chunk in order_chunks(chunks):
        chunk.apply(db)

    return db
