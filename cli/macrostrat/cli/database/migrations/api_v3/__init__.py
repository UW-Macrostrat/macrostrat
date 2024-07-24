from ..base import Migration

class BaselineMigration(Migration):
    name = "api-v3"
    subsystem = "core"
    description = """
    Apply the schema changes from https://github.com/UW-Macrostrat/api-v3 to the database
    """
    # Confirm that the tables created by the API v3 migrations are present
    expected_tables = [
        "storage.object_group", "storage.object", 
        "maps_metadata.ingest_process", "maps_metadata.ingest_process_tag",
        "macrostrat_auth.user", "macrostrat_auth.groups",
    ]

    depends_on = ['map-source-slug']
