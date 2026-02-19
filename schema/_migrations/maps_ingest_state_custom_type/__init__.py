from macrostrat.core.migrations import (
    Migration,
    ReadinessState,
    _not,
    custom_type_exists,
)
from macrostrat.database import Database, Identifier


def ingest_type_exists_in_wrong_schema(db: Database) -> bool:
    schemas = ["macrostrat_backup", "macrostrat", "public"]
    conditions = [custom_type_exists(schema, "ingest_state")(db) for schema in schemas]
    return any(conditions)


_schemas = ["macrostrat_backup", "macrostrat", "public"]


class MapsIngestStateCustomTypeMigration(Migration):
    name = "ingest-state-type"
    subsystem = "maps"
    description = """
    - Relocate custom types that drives the map ingestion process.
    - Remove duplicate custom types from the public schema.
    """
    readiness_state = ReadinessState.GA

    postconditions = [
        custom_type_exists("maps", "ingest_state"),
        custom_type_exists("maps", "ingest_type"),
        *(_not(custom_type_exists(schema, "ingest_state")) for schema in _schemas),
        *(_not(custom_type_exists(schema, "ingest_type")) for schema in _schemas),
    ]

    preconditions = [ingest_type_exists_in_wrong_schema]

    def apply(self, db: Database):
        # Handle edge case where the MariaDB migration has already been applied

        for schema in ["macrostrat_backup", "macrostrat", "public"]:
            db.run_sql(
                """
                ALTER TYPE {schema}.ingest_state SET SCHEMA maps;
                ALTER TYPE {schema}.ingest_type SET SCHEMA maps;

                DROP TYPE IF EXISTS {schema}.ingest_state;
                DROP TYPE IF EXISTS {schema}.ingest_type;
            """,
                dict(schema=Identifier(schema)),
            )
