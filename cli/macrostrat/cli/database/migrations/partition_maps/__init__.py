from pathlib import Path

from macrostrat.database import Database

from ..base import ApplicationStatus, Migration, exists, view_exists

__dir__ = Path(__file__).parent


class PartitionMapsMigration(Migration):
    name = "partition-maps"
    # This partition is required
    subsystem = "maps"
    description = """
    Starting from a Macrostrat v1 map database (burwell), integrate the tiny, small, medium, and large map tables (+lines)
    into a single map table, partitioned by scale to retain the original table structure and avoid copying data.
    """
    depends_on = ["macrostrat-core-v2"]

    postconditions = [
        exists("maps", "lines", "polygons"),
        view_exists("lines", "tiny", "small", "medium", "large"),
    ]
