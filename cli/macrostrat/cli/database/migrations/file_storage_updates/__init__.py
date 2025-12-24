from macrostrat.core.migrations import Migration, exists, has_columns, _not, _any


class MapFiles(Migration):
    name = "map-files"
    subsystem = "maps"
    description = "Update storage schema for better file management."
    depends_on = ["api-v3"]
    preconditions = [
        exists("maps_metadata", "ingest_process"),
        exists("storage", "object"),
    ]
    postconditions = [
        # storage.object no longer has object_group_id
        # intersection table exists in storage schema
        exists("storage", "map_files"),
        # intersection table columns exist
        has_columns(
            "maps_metadata",
            "map_files",
            "id",
            "ingest_process_id",
            "object_id",
        ),
    ]


class MapFilesChangeSchema(Migration):
    name = "map-files-change-schema"
    subsystem = "maps"
    description = "Change map_files table to use the map_metadata schema"
    depends_on = ["map-files"]
    preconditions = [
        exists("storage", "map_files"),
        exists("maps_metadata", "map_files"),
    ]
    postconditions = [_not(exists("storage", "map_files"))]

    def apply(self, db):
        db.run_sql(
            """
            INSERT INTO maps_metadata.map_files (ingest_process_id, object_id)
            SELECT ingest_process_id, object_id FROM storage.map_files
            ON CONFLICT (ingest_process_id, object_id) DO NOTHING;

            DROP TABLE IF EXISTS storage.map_files;
            """
        )


has_object_group = _any(
    [
        exists("storage", "object_group"),
        has_columns("storage", "object", "object_group_id"),
    ]
)


class StorageAddColumns(Migration):
    name = "storage-add-columns"

    def apply(self, db):
        db.run_sql(
            """
            ALTER TABLE storage.object DROP COLUMN IF EXISTS object_group_id;
            DROP TABLE IF EXISTS storage.object_group;
            """
        )

    preconditions = [has_object_group]

    postconditions = [
        _not(has_object_group),
    ]
