from pathlib import Path

from macrostrat.core.migrations import Migration, exists

migrations_dir = Path(__file__).parent / "migrations"


class InitialSchema(Migration):
    name = "rockd_initial_schema"
    description = "Initial schema and core tables"
    subsystem = "rockd_database"
    preconditions = [lambda db: True]
    postconditions = [exists("public", "people")]

    fixtures = [
        migrations_dir
        / "0010-rockd-dms-defs.sql",  # creates util functions in the rockd db for the tileserver api
        migrations_dir / "rockd-tile-utils.sql",
        migrations_dir / "0012_rockd_user_privileges.sql",  # grants/defaults (safe)
        migrations_dir / "0020_integration_tokens.sql",  # adds tokens for integrations
        migrations_dir / "0030_rockd-coords.sql",  # standalone table
        migrations_dir
        / "0040_model-feedback-schema.sql",  # references checkins/observations
        migrations_dir / "0050_strabo_integration.sql",  # references people
        migrations_dir / "0020_integration_tokens.sql",  # alters/inserts into people
    ]
