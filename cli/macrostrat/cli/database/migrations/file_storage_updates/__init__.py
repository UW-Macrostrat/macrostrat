from macrostrat.core.migrations import (
    Migration,
    column_type_is,
    exists,
    has_columns,
    not_exists,
    view_exists,
)


class FileStorageUpdates(Migration):
    name = "file-storage-updates"
    subsystem = "maps"
    description = "Update storage schema for better file management."
    depends_on = ["api-v3"]
    preconditions = [
        exists("storage", "object"),
        exists("storage", "object_group"),
        exists("maps_metadata", "ingest_process"),
    ]
    postconditions = [
        # storage.object no longer has object_group_id
        has_columns(
            "storage",
            "object",
            "scheme",
            "host",
            "bucket",
            "key",
            "source",
            "mime_type",
            "sha256_hash",
            "created_on",
            "updated_on",
            "deleted_on",
        ),
        # intersection table exists in storage schema
        exists("storage", "map_files"),
        # intersection table columns exist
        has_columns(
            "storage",
            "map_files",
            "id",
            "ingest_process_id",
            "object_id",
        ),
    ]
