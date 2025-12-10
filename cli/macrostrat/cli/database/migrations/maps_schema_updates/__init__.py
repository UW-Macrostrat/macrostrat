from macrostrat.core.migrations import Migration, column_type_is, exists, has_columns

class MapsSchemaUpdates(Migration):
    name = "maps-schema-updates"
    subsystem = "maps"
    depends_on = ["ingest-state-type", "maps-sources"]

    preconditions = [
        exists("maps", "sources"),
    ]
    postconditions = [
        column_type_is("maps", "polygons_large", "orig_id", "text"),
        column_type_is("maps", "polygons_medium", "orig_id", "text"),
        column_type_is("maps", "polygons_small", "orig_id", "text"),
        column_type_is("maps", "polygons_tiny", "orig_id", "text"),
        has_columns("maps", "sources", "license", "keywords", "language", "description",
                    "date_finalized", "ingested_by"),
    ]
