from macrostrat.core.migrations import Migration, view_exists
from macrostrat.core.migrations import has_columns


class MapsSourcesMetadataMigration(Migration):
    name = "maps-sources"
    subsystem = "core"
    description = """
    Create views for sources_metadata and ingest_process in the maps and macrostrat_api schemas
    """

    depends_on = ["api-v3", "column-builder"]

    postconditions = [
        view_exists("maps", "sources_metadata", "ingest_process"),
        view_exists(
            "macrostrat_api", "sources_metadata", "sources_ingestion", "sources"
        ),
        has_columns("maps", "sources", "is_finalized", "scale_denominator"),
    ]
