from pathlib import Path

from ...database import SubsystemSchemaDefinition

__here__ = Path(__file__).parent
fixtures_dir = __here__ / "fixtures"

legend_api = SubsystemSchemaDefinition(
    name="legend-api",
    fixtures=[fixtures_dir],
)
