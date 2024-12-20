from macrostrat.database import Database

from macrostrat.core.migrations import Migration, custom_type_exists


class MapsIngestStateCustomTypeMigration(Migration):
    name = "ingest-state-type"
    subsystem = "maps"
    description = """
    Relocate custom type that drives the maps ingest process
    """

    depends_on = ["baseline", "macrostrat-mariadb"]

    postconditions = [custom_type_exists("maps", "ingest_state")]

    preconditions = []

    def apply(self, db: Database):
        # Handle edge case where the MariaDB migration has already been applied
        db.run_sql("ALTER TYPE macrostrat_backup.ingest_state SET SCHEMA macrostrat")
        db.run_sql("ALTER TYPE macrostrat.ingest_state SET SCHEMA maps")
