from ..base import Migration, exists

class BaselineMigration(Migration):
    name = "api-v3"
    subsystem = "core"
    description = """
    Apply the schema changes from https://github.com/UW-Macrostrat/api-v3 to the database
    """

    depends_on = ['map-source-slug']

    # Confirm that the tables created by the API v3 migrations are present
    postconditions = [
        exists("storage","object_group","object"),
        exists("maps_metadata","ingest_process","ingest_process_tag"),
        exists("macrostrat_auth","user","group"),
    ]
