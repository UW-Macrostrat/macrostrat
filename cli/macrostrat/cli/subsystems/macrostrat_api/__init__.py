"""
The macrostrat_api subsystem defines the schema for the Macrostrat API, used
primarily in Macrostrat's column-builder application and set of routes.
"""

from pathlib import Path

from ...database import SubsystemSchemaDefinition

__here__ = Path(__file__).parent
fixtures_dir = __here__ / "schema"


macrostrat_api = SubsystemSchemaDefinition(
    name="macrostrat-api",
    fixtures=[fixtures_dir],
)
