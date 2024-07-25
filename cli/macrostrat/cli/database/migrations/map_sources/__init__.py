from macrostrat.database import Database
from ..base import Migration, view_exists, schema_exists

class MapsSourcesMetadataMigration(Migration):
    name = "maps-sources"
    subsystem = "core"
    description = """
    Starting from a database with migration map-source-slugs applied, create associated
    metadata views for maps.sources
    """

    depends_on = ["api-v3", "column-builder"]

    postconditions = [
        view_exists("maps", "sources_metadata", "ingest_process"),
        view_exists("macrostrat_api", "sources_metadata", "sources_ingestion", "sources"),
    ]
