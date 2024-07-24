from macrostrat.database import Database
from ..base import Migration, view_exists, schema_exists

class MapsSourcesMetadataMigration(Migration):
    name = "maps-sources"
    subsystem = "core"
    description = """
    Starting from a database with migration map-source-slugs applied, create associated
    metadata views for maps.sources
    """

    preconditions = [schema_exists("macrostrat_api")]

    postconditions = [
        view_exists("maps", "source_metadata"),
        view_exists("macrostrat_api", "sources_metadata", "sources_ingestion", "sources"),
    ]

    depends_on = ["api-v3", "column-builder"]

    def should_apply(self, database: Database):
        inst = database.inspector
        for schema, views in self.expected_views.items():
            if any(v not in inst.get_view_names(schema) for v in views):
                return True
