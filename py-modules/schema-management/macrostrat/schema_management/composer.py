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

from dataclasses import dataclass, field
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Callable, Optional, Union

from macrostrat.database import Database

# A provider that applies its own statements to the database.
DBCallable = Callable[[Database], None]

# A declarative provider: a directory of .sql files, or a callable.
Provider = Union[Path, DBCallable]


@dataclass
class SchemaDefinition:
    """A named, dependency-ordered unit of declarative schema.

    Providers are applied in listed order once the chunk's ``depends_on`` are
    satisfied. A ``Path`` provider is treated as a directory of ``.sql`` files;
    any other callable receives the :class:`Database` and applies its own
    statements.
    """

    name: str
    depends_on: list[str] = field(default_factory=list)
    provides: list[Provider] = field(default_factory=list)
    # Environments in which this chunk applies. ``None`` means all environments.
    environments: Optional[frozenset[str]] = None
    database: str = "macrostrat"

    def applies_to(self, env: str) -> bool:
        return self.environments is None or env in self.environments

    def apply(self, db: Database) -> None:
        for provider in self.provides:
            if isinstance(provider, Path):
                apply_sql_dir(db, provider)
            elif callable(provider):
                provider(db)
            else:
                raise TypeError(
                    f"Chunk {self.name!r} provider must be a Path or callable, "
                    f"got {provider!r}"
                )


def apply_sql_dir(db: Database, directory: Path) -> None:
    """Apply every ``.sql`` file under ``directory`` in filename order.

    Mirrors the globbing in :func:`apply_schema_for_environment` exactly: recurse,
    sort by path, drop ``*.plan.sql``. Duplicated (rather than shared) to keep the
    composer additive; the parity test guards against drift.
    """
    if not directory.exists():
        return
    fixtures = sorted(directory.rglob("*.sql"))
    fixtures = [f for f in fixtures if not f.name.endswith(".plan.sql")]
    if not fixtures:
        return
    db.run_fixtures(fixtures)


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
