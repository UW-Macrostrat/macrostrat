"""Progressive, chunk-based schema builder for tests.

The harness applies the schema one subsystem chunk at a time, in dependency
order, so a test database can be grown incrementally: a minimal single-subsystem
build, a full build, or anything in between. Already-applied chunks are skipped,
so successive calls extend the database rather than rebuild it.

By default it applies the ``optimize`` transform, which skips DDL that is
unnecessary for most tests (indexes, grants, ownership) — a significant speedup
with few penalties.
"""

from typing import Optional

from macrostrat.core import SchemaDefinition
from macrostrat.database import Database
from macrostrat.database.query import StatementContext, StatementResult

from .chunks import chunks_for_environment
from .composer import dependency_closure, order_chunks


def optimize_transform(ctx: StatementContext) -> Optional[list[StatementResult]]:
    """Drop statements not needed for most tests, for a faster build.

    Returning ``[]`` skips the statement; ``None`` applies it unchanged.
    """
    stmt = ctx.sql_text.strip().lower()
    if (
        stmt.startswith("create index")
        or stmt.startswith("create unique index")
        or stmt.startswith("alter index")
        or stmt.startswith("grant")
        or (stmt.startswith("alter table") and "owner to" in stmt)
    ):
        return []
    return None


class DatabaseTestHarness:
    """Build a Macrostrat test database progressively, chunk by chunk."""

    def __init__(
        self,
        database: Database,
        *,
        env: Optional[str] = None,
        optimize: bool = True,
    ):
        from macrostrat.core.config import settings

        self.db = database
        self.env = env or settings.env
        self.optimize = optimize
        # Names of chunks that have been applied.
        self._applied_chunks: set[str] = set()

    @property
    def transform_statement(self):
        return optimize_transform if self.optimize else None

    def chunks(self) -> list[SchemaDefinition]:
        """Chunks for this environment, in dependency order."""
        return order_chunks(chunks_for_environment(self.env))

    def load_schema(self, *, target: Optional[str] = None) -> Database:
        """Progressively apply schema chunks in dependency order.

        :param target: a subsystem (chunk) name. Only that chunk and its
            transitive dependencies are built — e.g. ``target="macrostrat"``
            gives the minimal "macrostrat schema only" build. When omitted, the
            full schema for the environment is built.

        Chunks already applied by a previous call are skipped, so a minimal build
        can be grown into a fuller one in place.
        """
        chunks = self.chunks()
        if target is not None:
            keep = dependency_closure(chunks, target)
            chunks = [c for c in chunks if c.name in keep]

        for chunk in chunks:
            if chunk.name in self._applied_chunks:
                continue
            chunk.apply(self.db, transform_statement=self.transform_statement)
            self._applied_chunks.add(chunk.name)
        return self.db
