from pathlib import Path

from sqlalchemy.engine import make_url

from macrostrat.core import app as app_
from macrostrat.database import Database
from macrostrat.schema_management.migrations import (
    ApplicationStatus,
    Migration,
    exists,
    has_columns,
    schema_exists,
)

migrations_dir = Path(__file__).parent


class RockdMigration(Migration):
    """Base class for rockd migrations."""

    subsystem = "rockd"


class InitialSchema(RockdMigration):
    name = "initial-schema"
    description = "Initial schema and core tables"
    postconditions = [exists("public", "people")]

    def should_apply(self, database: Database) -> ApplicationStatus:
        # Default to applied
        return ApplicationStatus.APPLIED

    def apply(self, database: Database) -> None:
        # Initial schema is applied outside the migration system
        raise NotImplementedError(
            "Initial schema is applied outside the migration system."
        )


class RockdTileUtils(RockdMigration):
    name = "tile-utils"
    readiness_state = "ga"
    description = "Rockd tile utility functions"

    postconditions = [
        # Check if the tile_utils schema exists
        schema_exists("tile_utils"),
    ]

    fixtures = [
        migrations_dir
        / "0010-rockd-tms-defs.sql",  # creates util functions in the rockd db for the tileserver api
        migrations_dir / "0011-rockd-tile-utils.sql",
    ]


class UsageStatsTable(RockdMigration):
    name = "usage-stats-table"
    readiness_state = "beta"
    description = "Create usage_stats table"
    postconditions = [
        # Check if the usage_stats table exists
        exists("public", "usage_stats"),
    ]

    fixtures = [
        migrations_dir / "0030-usage-stats-table.sql",  # standalone table
    ]


class ModelFeedbackSchema(RockdMigration):
    name = "model-feedback-schema"
    readiness_state = "beta"
    description = "Add model feedback schema"
    postconditions = [
        # Check if the model_feedback table exists
        exists("public", "model_feedback"),
    ]

    fixtures = [
        migrations_dir
        / "0040-model-feedback-schema.sql",  # references checkins/observations
    ]


class StraboIntegration(RockdMigration):
    name = "strabo-integration"
    readiness_state = "beta"
    description = "Add Strabo integration tables"
    postconditions = [
        # Check if the strabo_integrations table exists
        exists("user_features", "linked_strabo_account"),
        has_columns("public", "checkins", "spot_id"),
    ]

    fixtures = [
        migrations_dir / "0050-strabo-integration.sql",  # references people
    ]


class StraboAddSpot(RockdMigration):
    name = "strabo-add-spot"
    readiness_state = "ga"
    description = "Add Strabo spot_id to checkins table"
    postconditions = [
        has_columns("public", "checkins", "spot_id"),
    ]

    fixtures = [
        migrations_dir / "0051-strabo_add_spot.sql",
    ]


class UserPrivileges(RockdMigration):
    name = "user-privileges"
    readiness_state = "ga"
    description = "Set default user privileges"
    always_apply = True
    fixtures = [
        migrations_dir / "0012-user-privileges.sql",  # grants/defaults (safe)
    ]


class IntegrationTokens(RockdMigration):
    name = "integration-tokens"
    readiness_state = "beta"
    description = "Schema updates and new tables"
    depends_on = [
        "initial-schema",
    ]
    postconditions = [
        # Check if the tile_utils schema exists
        has_columns("public", "people", "token_exp")
    ]
    fixtures = [
        migrations_dir / "0020-integration-tokens.sql",  # adds tokens for integrations
    ]


class CreateForeignTables(RockdMigration):
    name = "foreign-tables"
    readiness_state = "ga"
    description = "Creates foreign macrostrat tables for the Rockd api to query."

    def apply(self, database: Database) -> None:
        url_str = app_.settings.get("pg_database")
        if not url_str:
            raise RuntimeError("Set pg_database in your environment")

        url = make_url(url_str)
        fdw_host = url.host or ""
        fdw_user = url.username or ""
        fdw_password = url.password or ""
        print(f"Creating foreign tables from target: host={fdw_host}, user={fdw_user}")

        sql_template = (migrations_dir / "0060-create-foreign-tables.sql").read_text()

        # inject variables!
        sql = (
            sql_template.replace("{fdw_host}", fdw_host)
            .replace("{fdw_user}", fdw_user)
            .replace("{fdw_password}", fdw_password)
        )

        with database.engine.connect() as conn:
            conn = conn.execution_options(isolation_level="AUTOCOMMIT")
            print("Dropping existing foreign tables and server...")
            conn.exec_driver_sql(sql)
            print("Foreign tables created successfully!")
