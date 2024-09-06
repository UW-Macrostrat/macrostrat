from pathlib import Path

from macrostrat.database import Database

from ..base import Migration, exists, has_fks

__dir__ = Path(__file__).parent


class MacrostratCoreMigration(Migration):
    name = "macrostrat-mariadb"
    # This partition is required
    subsystem = "core"
    description = """
    Populate the `macrostrat` schema of the database prior to importing data from mariadb
    """
    depends_on = ["baseline"]

    postconditions = [
        exists("macrostrat", "projects", "sections", "strat_tree", "unit_boundaries")
    ]
