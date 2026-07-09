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

from macrostrat.core import SchemaDefinition
from macrostrat.database import Database


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


def dependency_closure(chunks: list[SchemaDefinition], target: str) -> set[str]:
    """Names of ``target`` plus all of its transitive dependencies.

    ``target`` is a subsystem (chunk) name. Building the closure yields exactly
    the chunks needed to stand up that subsystem — this replaces the old
    filename-substring ``target`` matching.
    """
    by_name = {c.name: c for c in chunks}
    if target not in by_name:
        raise ValueError(
            f"Unknown schema target {target!r}. Known chunks: {sorted(by_name)}"
        )

    seen: set[str] = set()
    stack = [target]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        chunk = by_name.get(name)
        if chunk is not None:
            stack.extend(chunk.depends_on)
    return seen


def selected_chunks(
    env: str, *, target: Optional[str] = None, no_dependents: bool = False
) -> list[SchemaDefinition]:
    """Ordered chunks for ``env``, optionally narrowed to a ``target`` subsystem.

    - ``target=None`` → all chunks for the environment.
    - ``target`` set, ``no_dependents=False`` (default) → the target chunk plus
      its dependency closure (the chunks it depends on).
    - ``target`` set, ``no_dependents=True`` → only the target chunk.
    """
    from .chunks import chunks_for_environment

    chunks = order_chunks(chunks_for_environment(env))
    if target is None:
        return chunks

    names = {c.name for c in chunks}
    if target not in names:
        raise ValueError(f"Unknown target {target!r}. Known chunks: {sorted(names)}")

    keep = {target} if no_dependents else dependency_closure(chunks, target)
    return [c for c in chunks if c.name in keep]


def build_schema(
    db: Database,
    env: str,
    chunks: Optional[list[SchemaDefinition]] = None,
    *,
    transform_statement=None,
    statement_filter=None,
    target: Optional[str] = None,
) -> Database:
    """Build the declarative schema for ``env`` by applying chunks in graph order.

    ``transform_statement`` / ``statement_filter`` are forwarded to SQL file
    application. If ``target`` is given (a subsystem/chunk name), only that chunk
    and its transitive dependencies are built — the minimal build for that
    subsystem.
    """
    if chunks is None:
        # Imported lazily to avoid a circular import at module load.
        from .chunks import chunks_for_environment

        chunks = chunks_for_environment(env)

    ordered = order_chunks(chunks)
    if target is not None:
        keep = dependency_closure(chunks, target)
        ordered = [c for c in ordered if c.name in keep]

    for chunk in ordered:
        chunk.apply(
            db,
            transform_statement=transform_statement,
            statement_filter=statement_filter,
        )

    return db
