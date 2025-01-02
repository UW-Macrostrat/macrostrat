from macrostrat.database import Database

from macrostrat.core.migrations import Migration, has_columns

condition = has_columns("maps_metadata", "ingest_process", "ui_state")


class IngestMetadataMigration(Migration):
    name = "ingest-metadata"

    depends_on = ["api-v3", "macrostrat-api"]

    postconditions = [condition]

    def apply(self, db: Database):
        db.run_sql(
            """
            ALTER TABLE maps_metadata.ingest_process ADD COLUMN ui_state jsonb;
            """
        )
