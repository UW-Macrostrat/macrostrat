from macrostrat.core.migrations import (
    Migration,
    column_type_is,
    has_columns,
    view_exists,
)


class IngestPreprocessUpdates(Migration):
    name = "ingest-preprocess-updates"
    subsystem = "maps"
    description = "Align maps_metadata.ingest_process table across envs."
    depends_on = ["ingest-state-type"]

    preconditions = [
        has_columns("maps_metadata", "ingest_process", "id"),
    ]
    postconditions = [
        has_columns(
            "maps_metadata",
            "ingest_process",
            "polygon_state",
            "line_state",
            "point_state",
            "ingest_pipeline",
            "map_url",
            "ingested_by",
            "slug",
        ),
        # Column types match development
        column_type_is("maps_metadata", "ingest_process", "polygon_state", "JSONB"),
        column_type_is("maps_metadata", "ingest_process", "line_state", "JSONB"),
        column_type_is("maps_metadata", "ingest_process", "point_state", "JSONB"),
        column_type_is("maps_metadata", "ingest_process", "ingest_pipeline", "TEXT"),
        column_type_is("maps_metadata", "ingest_process", "map_url", "TEXT"),
        column_type_is("maps_metadata", "ingest_process", "ingested_by", "TEXT"),
        column_type_is("maps_metadata", "ingest_process", "slug", "TEXT"),
        # View must exist after migration
        view_exists("macrostrat_api", "map_ingest_metadata"),
        view_exists("macrostrat_api", "map_ingest"),
        view_exists("macrostrat_api", "map_ingest_tags"),

    ]
