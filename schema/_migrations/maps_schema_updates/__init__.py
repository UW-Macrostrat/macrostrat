from macrostrat.schema_management import (
    Migration,
    ReadinessState,
    column_type_is,
    exists,
    has_columns,
)


class MapsSchemaUpdates(Migration):
    name = "maps-schema-updates"
    subsystem = "maps"
    depends_on = ["ingest-state-type", "maps-sources"]
    readiness_state = ReadinessState.GA

    preconditions = [
        exists("maps", "sources"),
    ]
    postconditions = [
        # Read off the parent tables: the scale partitions this retyped are views
        # once `maps-polygons-flat` / `maps-lines-flat` have run.
        column_type_is("maps", "polygons", "orig_id", "text"),
        column_type_is("maps", "lines", "orig_id", "text"),
        column_type_is("maps", "points", "orig_id", "text"),
        has_columns(
            "maps",
            "sources",
            "license",
            "keywords",
            "language",
            "description",
            "date_finalized",
            "ingested_by",
        ),
        exists("maps", "large"),
        exists("maps", "medium"),
        exists("maps", "small"),
        exists("maps", "tiny"),
        exists("lines", "large"),
        exists("lines", "medium"),
        exists("lines", "small"),
        exists("lines", "tiny"),
        exists("points", "points"),
    ]
