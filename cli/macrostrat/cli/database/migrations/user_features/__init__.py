from macrostrat.core.migrations import Migration, exists


class UserFeaturesMigration(Migration):
    name = "user-features"
    subsystem = "core"
    description = """
    Apply the schema changes to the database
    """

    depends_on = ["map-source-slug"]

    # Confirm that the tables created by the API v3 migrations are present
    postconditions = [
        exists("storage", "object_group", "object"),
        exists("maps_metadata", "ingest_process", "ingest_process_tag"),
        exists("macrostrat_auth", "user", "group"),
    ]
