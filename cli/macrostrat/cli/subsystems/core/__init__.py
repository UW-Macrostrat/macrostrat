from pathlib import Path

from ...database import SubsystemSchemaDefinition
from ...database.utils import grant_permissions

__here__ = Path(__file__).parent

core_schema = SubsystemSchemaDefinition(
    name="core",
    # All this does is grant usage of the macrostrat, maps, and carto_new schemas
    # to the macrostrat role
    fixtures=[
        grant_permissions(schema, "macrostrat", "SELECT")
        for schema in ["macrostrat", "maps", "carto_new"]
    ],
)
