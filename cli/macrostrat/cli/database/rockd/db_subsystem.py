from macrostrat.core import MacrostratSubsystem, app
from .database import get_rockd_db
from pathlib import Path

fixtures_dir = Path(__file__).parent / "fixtures"

class RockdDatabaseSubsystem(MacrostratSubsystem):
    name = "rockd_database"

    def initialize(self):
        self.register_schema_part(name="core", fixtures=[fixtures_dir])

rockd_subsystem = RockdDatabaseSubsystem(app)
