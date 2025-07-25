from pathlib import Path

from macrostrat.core.migrations import Migration, exists


class SgpMigration(Migration):
    name = "sgp-integration"
    subsystem = "sgp"
    description = """Create tables for SGP matching"""

    depends_on = ["baseline"]

    fixtures = [
        Path(__file__).parent / "sql" / "schema.sql",
    ]

    postconditions = [exists("integrations", "sgp_matches")]
