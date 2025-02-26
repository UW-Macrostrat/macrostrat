from macrostrat.core.migrations import Migration, has_columns, view_exists


class MapsSourcesAPIMigration(Migration):
    name = "maps-sources-api"
    subsystem = "maps"
    description = """
    Create views for sources_metadata and ingest_process in the maps and macrostrat_api schemas
    """

    depends_on = ["baseline"]

    postconditions = [
        view_exists(
            "macrostrat_api", "sources_metadata", "sources_ingestion", "sources"
        ),
        has_columns(
            "macrostrat_api",
            "sources",
            "is_finalized",
            "scale_denominator",
            "lines_oriented",
            allow_view=True,
        ),
    ]
