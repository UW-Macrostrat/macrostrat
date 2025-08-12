from pathlib import Path

from macrostrat.core import MacrostratSubsystem, app

from .database import get_rockd_db

migrations_dir = Path(__file__).parent / "migrations"


class RockdDatabaseSubsystem(MacrostratSubsystem):
    name = "rockd_database"

    def get_db(self):
        return get_rockd_db()

    def initialize(self):
        selected_fixtures = [
            migrations_dir / "0010_rockd_user_privileges.sql",  # grants/defaults (safe)
            migrations_dir / "0030_rockd-coords.sql",  # standalone table
            migrations_dir
            / "0040_model-feedback-schema.sql",  # references checkins/observations
            migrations_dir / "0050_strabo_integration.sql",  # references people
            migrations_dir
            / "0020_integration_tokens.sql",  # alters/inserts into people
        ]
        self.register_schema_part(
            name="rockd_initial_schema", fixtures=selected_fixtures
        )


rockd_subsystem = RockdDatabaseSubsystem(app)
