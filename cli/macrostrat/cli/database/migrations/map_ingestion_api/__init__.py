from pathlib import Path

from macrostrat.cli.database import setup_postgrest_access
from macrostrat.core.migrations import Migration, view_exists

__dir__ = Path(__file__).parent


class MapsPostgrestAPI(Migration):
    name = "map-ingestion-api"
    # This partition is required
    subsystem = "map-ingestion"
    description = """
    Add a basic postgrest API for map ingestion schema
    """
    depends_on = ["maps-source-operations"]

    postconditions = [
        view_exists("map_ingestion_api", "line_types", "point_types", "maps"),
    ]

    fixtures = [
        __dir__,
        setup_postgrest_access(
            "map_ingestion_api",
            read_user="web_user",
            write_user="web_user",
        ),
    ]
