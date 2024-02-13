from pathlib import Path

from ...database import SubsystemSchemaDefinition

__here__ = Path(__file__).parent
fixtures_dir = __here__ / "fixtures"

kg_schema = SubsystemSchemaDefinition(
    name="knowledge-graph",
    fixtures=[fixtures_dir],
)
