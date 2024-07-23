from ..base import Migration
from macrostrat.database import Database
from pathlib import Path

__dir__ = Path(__file__).parent


class PartitionMapsMigration(Migration):
    name = "partition-maps"
    # This partition is required
    subsystem = "maps"
    description = """
    Starting from a Macrostrat v1 map database (burwell), integrate the tiny, small, medium, and large map tables (+lines)
    into a single map table, partitioned by scale to retain the original table structure and avoid copying data.
    """

    def should_apply(self, db: Database):
        # Check if the maps.polygons table exists
        insp = db.inspector

        if self.is_satisfied(db):
            return False

        for scale in ["tiny", "small", "medium", "large"]:
            if not db.inspector.has_table(scale, schema="maps") and not insp.has_table(
                scale, schema="lines"
            ):
                return False
        return True

    def is_satisfied(self, db: Database):
        for table in ["lines", "polygons"]:
            if not db.inspector.has_table(table, schema="maps"):
                return False
        return True

    def apply(self, db: Database):
        # We should sync this with the 'engine' configuration
        db.run_fixtures(__dir__)
