from macrostrat.core.migrations import Migration, _not, custom_type_exists
from macrostrat.database import Database


class MapsIngestStateCustomTypeMigration(Migration):
    name = "ingest-state-type"
    subsystem = "maps"
    description = """
    - Relocate custom types that drives the map ingestion process.
    - Remove duplicate custom types from the public schema.
    """

    depends_on = ["baseline", "macrostrat-mariadb"]

    postconditions = [
        custom_type_exists("maps", "ingest_state"),
        custom_type_exists("maps", "ingest_type"),
        _not(custom_type_exists("public", "ingest_state")),
        _not(custom_type_exists("public", "ingest_type")),
    ]

    preconditions = []

    def apply(self, db: Database):
        # Handle edge case where the MariaDB migration has already been applied
        db.run_sql("ALTER TYPE macrostrat_backup.ingest_state SET SCHEMA macrostrat")
        db.run_sql("ALTER TYPE macrostrat.ingest_state SET SCHEMA maps")

        db.run_sql("ALTER TYPE macrostrat_backup.ingest_type SET SCHEMA macrostrat")
        db.run_sql("ALTER TYPE macrostrat.ingest_type SET SCHEMA maps")

        db.run_sql("DROP TYPE IF EXISTS public.ingest_state")
        db.run_sql("DROP TYPE IF EXISTS public.ingest_type")
