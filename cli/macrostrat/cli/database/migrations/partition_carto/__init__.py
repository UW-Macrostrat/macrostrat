from ..base import Migration, not_exists, view_exists
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

    postconditions = [
        view_exists('carto_new', 'lines_tiny', 'lines_small', 'lines_medium', 'lines_large'),
        view_exists('carto_new', 'tiny', 'small', 'medium', 'large'),
    ]
