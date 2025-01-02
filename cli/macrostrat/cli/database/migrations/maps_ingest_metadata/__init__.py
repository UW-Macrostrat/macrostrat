from macrostrat.core.migrations import Migration, has_columns, view_exists


class IngestMetadataMigration(Migration):
    name = "ingest-metadata"

    depends_on = ["api-v3", "macrostrat-api"]

    postconditions = [
        has_columns("maps_metadata", "ingest_process", "ui_state"),
        view_exists("macrostrat_api", "map_ingest_metadata"),
    ]
