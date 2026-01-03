from pathlib import Path

from macrostrat.core.migrations import Migration, exists

__dir__ = Path(__file__).parent


class MacrostratCoreMigration(Migration):
    name = "macrostrat-mariadb"
    # This partition is required
    subsystem = "core"
    description = """
    Populate the `macrostrat` schema of the database prior to importing data from mariadb
    """
    depends_on = ["baseline"]
    readiness_state = "ga"

    postconditions = [
        exists("macrostrat", "projects", "sections", "strat_tree", "unit_boundaries")
    ]
