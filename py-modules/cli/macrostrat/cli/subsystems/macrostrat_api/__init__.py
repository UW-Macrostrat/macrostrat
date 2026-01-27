"""
The macrostrat_api subsystem defines the schema for the Macrostrat API, used
primarily in Macrostrat's column-builder application and set of routes.
"""

from pathlib import Path

from macrostrat.app_frame import compose
from macrostrat.core import MacrostratSubsystem

from ...database import get_db
from ...database.utils import setup_postgrest_access

__here__ = Path(__file__).parent
fixtures_dir = __here__ / "schema"


class MacrostratAPISubsystem(MacrostratSubsystem):
    name = "macrostrat-api"

    def on_schema_update(self):
        """Set permissions on tables in the Macrostrat API subsystem
        TODO: make this only apply the minimum set of changes given the current
        GRANTs on the tables

        NOTE: this hook runs no matter which subsystems are being updated
        """
        self.app.console.print("Setting roles for Macrostrat API", style="green bold")
        db = get_db()

        setup_postgrest_access("macrostrat_api")(db)

        self.app.console.print(
            "Reloading the PostgREST schema cache", style="green bold"
        )
        db.run_sql("NOTIFY pgrst, 'reload schema';")
        # If we are running in a compose environment, reload the PostgREST service.
        # This should not be strictly necessary, but it makes extra sure that we've
        # fully reloaded the schema.
        if self.app.settings.get("compose_root", None) is not None:
            compose("kill -s SIGUSR1 postgrest")
