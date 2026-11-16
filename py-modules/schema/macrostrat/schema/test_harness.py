"""Build a Macrostrat test database progressively, chunk by chunk."""

from typing import Optional

from macrostrat.database import Database
from macrostrat.schema_management import harness

from .chunks import chunks_for_environment

optimize_transform = harness.optimize_transform


class DatabaseTestHarness(harness.DatabaseTestHarness):
    """The library's harness, over the chunks of a Macrostrat environment."""

    def __init__(
        self, database: Database, *, env: Optional[str] = None, optimize: bool = True
    ):
        from macrostrat.core.config import settings

        self.env = env or settings.env
        super().__init__(database, chunks_for_environment(self.env), optimize=optimize)
