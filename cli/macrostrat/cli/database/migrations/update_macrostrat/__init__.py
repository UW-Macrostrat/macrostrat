from ..base import Migration
from macrostrat.database import Database
from pathlib import Path

__dir__ = Path(__file__).parent


class MacrostratCoreMigration(Migration):
    name = "macrostrat-core-v2"
    # This partition is required
    subsystem = "core"
    description = """
    Update the Macrostrat core schema ('macrostrat') with foreign keys and data transformations to
    stabilize the schema in PostgreSQL after transformation from MariaDB.
    """
    # TODO: break this into smaller atomic migrations

    def should_apply(self, db: Database):
        # Check if foreign keys exist
        for table in ["units", "sections"]:
            if not db.inspector.has_table(table, schema="macrostrat"):
                return False

        return not self.is_satisfied(db)

    def is_satisfied(self, db: Database):
        # Check if foreign keys exist
        for table in ["units", "sections"]:
            fks = db.inspector.get_foreign_keys(table, schema="macrostrat")
            if len(fks) == 0:
                return False

    def apply(self, db: Database):
        # We should sync this with the 'engine' configuration
        db.run_fixtures(__dir__, params={})
