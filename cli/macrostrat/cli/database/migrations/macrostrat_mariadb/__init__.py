from ..base import Migration, exists, has_fks
from macrostrat.database import Database
from pathlib import Path

__dir__ = Path(__file__).parent


class MacrostratCoreMigration(Migration):
    name = "macrostrat-mariadb"
    # This partition is required
    subsystem = "core"
    description = """
    Populate the `macrostrat` schema of the database prior to importing data from mariadb
    """
    depends_on = ['api-v3']

    postconditions = [exists('macrostrat', 'projects', 'sections', 'strat_tree', 'unit_boundaries')]
