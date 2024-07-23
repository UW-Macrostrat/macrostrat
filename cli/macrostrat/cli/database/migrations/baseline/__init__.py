from ..base import Migration
from macrostrat.database import Database
from pathlib import Path

__dir__ = Path(__file__).parent


class BaselineMigration(Migration):
    name = "baseline"
    # This partition is required
    subsystem = "maps"
    description = """
    Starting from an empty database, create the baseline macrostrat schemas as of 2023-08-29. 
    """

    def should_apply(self, db: Database):
        # Basic sanity check, check if the carto schema exist
        insp = db.inspector
        return not insp.has_schema("carto")

    def apply(self, db: Database):
        # We should sync this with the 'engine' configuration
        db.run_fixtures(__dir__)
