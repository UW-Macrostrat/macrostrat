"""
The macrostrat_api subsystem defines the schema for the Macrostrat API, used
primarily in Macrostrat's column-builder application and set of routes.
"""

from pathlib import Path

from ...database import SubsystemSchemaDefinition, get_db
from macrostrat.core import MacrostratSubsystem
from macrostrat.app_frame import compose

__here__ = Path(__file__).parent
fixtures_dir = __here__ / "schema"


macrostrat_api = SubsystemSchemaDefinition(
    name="macrostrat-api",
    fixtures=[fixtures_dir],
)

# TODO: get schema migrations/fixtures to align with subsystems


class MacrostratAPISubsystem(MacrostratSubsystem):
    name = "macrostrat-api"

    def on_schema_update(self):
        """Set permissions on tables in the Macrostrat API subsystem
        TODO: make this only apply the minimum set of changes given the current
        GRANTs on the tables
        """
        self.app.console.print("Setting roles for Macrostrat API", style="green bold")
        db = get_db()
        db.run_sql(
            """
            GRANT USAGE ON SCHEMA macrostrat_api TO web_anon;
            GRANT USAGE ON SCHEMA macrostrat_api TO web_user;
            GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat_api TO web_anon;
            GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat_api TO web_user;
            """
        )

        self.app.console.print(
            "Reloading the PostgREST schema cache", style="green bold"
        )
        db.run_sql("NOTIFY pgrst, 'reload schema';")
        # If we are running in a compose environment, reload the PostgREST service.
        # This should not be strictly necessary, but it makes extra sure that we've
        # fully reloaded the schema.
        if self.app.settings.get("compose_root", None) is not None:
            compose("kill -s SIGUSR1 postgrest")
