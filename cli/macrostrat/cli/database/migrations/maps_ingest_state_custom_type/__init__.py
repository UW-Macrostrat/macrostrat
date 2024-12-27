from macrostrat.database import Database

from macrostrat.core.migrations import Migration, _not, custom_type_exists


def ingest_type_exists_in_wrong_schema(db: Database) -> bool:
    schemas = ["macrostrat_backup", "macrostrat", "public"]
    conditions = [custom_type_exists(schema, "ingest_state")(db) for schema in schemas]
    return any(conditions)


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
        _not(custom_type_exists("macrostrat", "ingest_state")),
        _not(custom_type_exists("macrostrat", "ingest_type")),
    ]

    preconditions = [ingest_type_exists_in_wrong_schema]

    def apply(self, db: Database):
        # Handle edge case where the MariaDB migration has already been applied
        db.run_sql("ALTER TYPE macrostrat_backup.ingest_state SET SCHEMA macrostrat")
        db.run_sql("ALTER TYPE macrostrat.ingest_state SET SCHEMA maps")

        db.run_sql("ALTER TYPE macrostrat_backup.ingest_type SET SCHEMA macrostrat")
        db.run_sql("ALTER TYPE macrostrat.ingest_type SET SCHEMA maps")

        db.run_sql("ALTER TYPE public.ingest_state SET SCHEMA maps")
        db.run_sql("ALTER TYPE public.ingest_type SET SCHEMA maps")
