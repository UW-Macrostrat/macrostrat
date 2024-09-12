from macrostrat.database import Database

from ..base import Migration, custom_type_exists


class MapsScaleCustomTypeMigration(Migration):
    name = "maps-scale-type"
    subsystem = "maps"
    description = """
    Relocate custom type that drives the maps schema
    """

    depends_on = ["baseline", "macrostrat-mariadb"]

    postconditions = [custom_type_exists("maps", "map_scale")]

    preconditions = []

    def apply(self, db: Database):
        # Handle edge case where the MariaDB migration has already been applied
        db.run_sql("ALTER TYPE macrostrat_backup.map_scale SET SCHEMA macrostrat")
        db.run_sql("ALTER TYPE macrostrat.map_scale SET SCHEMA maps")
