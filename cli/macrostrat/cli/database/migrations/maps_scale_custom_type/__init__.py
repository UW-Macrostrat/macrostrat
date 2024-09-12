from macrostrat.database import Database

from .. import ApplicationStatus
from ..base import Migration


class MapsScaleCustomTypeMigration(Migration):
    name = "maps-scale-type"
    subsystem = "maps"
    description = """
    Relocate custom type that drives the maps schema
    """

    depends_on = ["maps-sources"]

    postconditions = []

    preconditions = []

    def apply(self, db: Database) -> ApplicationStatus:
        # Handle edge case where the MariaDB migration has already been applied
        db.run_sql("ALTER TYPE macrostrat_backup.map_scale SET SCHEMA macrostrat")

        db.run_sql("ALTER TYPE macrostrat.map_scale SET SCHEMA maps")
