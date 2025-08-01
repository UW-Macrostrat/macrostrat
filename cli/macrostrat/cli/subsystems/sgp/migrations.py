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


class SGPAPIViewsMigration(Migration):
    name = "sgp-api-views"
    subsystem = "sgp"
    description = """Create views for SGP API integration"""

    depends_on = ["sgp-integration", "macrostrat-api"]

    fixtures = [
        Path(__file__).parent / "sql" / "api-views.sql",
    ]

    always_apply = True
