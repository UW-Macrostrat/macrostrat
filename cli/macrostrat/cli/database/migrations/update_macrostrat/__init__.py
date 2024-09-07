from pathlib import Path

from macrostrat.database import Database

from ..base import Migration, exists, has_fks

__dir__ = Path(__file__).parent


# TODO: break this into smaller atomic migrations
class MacrostratCoreMigration(Migration):
    name = "macrostrat-core-v2"
    # This partition is required
    subsystem = "core"
    description = """
    Update the Macrostrat core schema ('macrostrat') with foreign keys and data transformations to
    stabilize the schema in PostgreSQL after transformation from MariaDB.
    """
    depends_on = ["macrostrat-mariadb", "api-v3"]

    postconditions = [
        exists("macrostrat", "units", "sections"),
        has_fks("macrostrat", "units", "sections"),
    ]
