from pathlib import Path

from macrostrat.core.migrations import Migration, view_exists

__dir__ = Path(__file__).parent


class PartitionCartoMigration(Migration):
    name = "partition-carto"
    subsystem = "maps"
    description = """
    Starting from a Macrostrat v1 map database (burwell), integrate the tiny, small, medium, and large map tables (+lines)
    into a single map table, partitioned by scale to retain the original table structure and avoid copying data.
    """

    depends_on = ["partition-maps"]

    destructive = True

    postconditions = [
        view_exists(
            "carto_new", "lines_tiny", "lines_small", "lines_medium", "lines_large"
        ),
        view_exists("carto_new", "tiny", "small", "medium", "large"),
    ]
