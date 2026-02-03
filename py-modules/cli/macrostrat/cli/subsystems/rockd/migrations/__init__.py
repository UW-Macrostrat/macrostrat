from pathlib import Path

from macrostrat.core.migrations import (
    ApplicationStatus,
    Migration,
    exists,
    has_columns,
    schema_exists,
)
from macrostrat.database import Database

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
