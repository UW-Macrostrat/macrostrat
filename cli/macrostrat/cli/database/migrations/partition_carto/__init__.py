from ..base import Migration
from macrostrat.database import Database
from pathlib import Path

__dir__ = Path(__file__).parent


class PartitionCartoMigration(Migration):
    name = "partition-carto"
    subsystem = "maps"
    description = """
    Starting from a Macrostrat v1 map database (burwell), integrate the tiny, small, medium, and large map tables (+lines)
    into a single map table, partitioned by scale to retain the original table structure and avoid copying data.
    """

    depends_on = ['macrostrat-core-v2']

    def should_apply(self, db: Database):
        # Check if the maps.polygons table exists
        self.expected_tables = []

        for table in ["lines", "polygons"]:
            self.expected_tables.append(f"carto.{table}")

        for scale in ["tiny", "small", "medium", "large"]:
            self.expected_tables.append(f"carto_new.{scale}")
            self.expected_tables.append(f"carto_new.lines_{scale}")

        return super().should_apply(db)
