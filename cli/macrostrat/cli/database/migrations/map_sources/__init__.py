from macrostrat.database import Database
from ..base import Migration

class MapsSourcesMetadataMigration(Migration):
    name = "02-maps-sources-metadata"
    subsystem = "core"
    description = """
    Starting from a database with migration 01-map-source-slugs applied, create associated
    metadata views for maps.sources
    """
    expected_views = {
        'maps': ['sources_metadata'],
        'macrostrat_api': ['sources_metadata', 'sources_ingestion', 'sources']
    }

    def should_apply(self, database: Database):
        inst = database.inspector
        for schema, views in self.expected_views.items():
            if any(v not in inst.get_view_names(schema) for v in views):
                return True
