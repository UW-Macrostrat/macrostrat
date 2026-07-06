from macrostrat.database import Database

from .defs import apply_schema_for_environment


class DatabaseTestHarness:
    def __init__(self, database: Database):
        self.db = database

    def load_schema(self, target: str | None = None):
        from macrostrat.core.config import settings

        apply_schema_for_environment(
            self.db,
            env=settings.env,
            target=target,
        )
