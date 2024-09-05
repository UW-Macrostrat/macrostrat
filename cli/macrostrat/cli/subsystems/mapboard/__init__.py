from macrostrat.core import MacrostratSubsystem
from typer import Typer


class MapboardSubsystem(MacrostratSubsystem):
    name = "mapboard"

    def on_add_commands(self, cli):
        cmd = Typer(no_args_is_help=True, short_help="Macrostrat Mapboard commands")

        @cmd.command("export-mapboard", rich_help_panel="Export")
        def export_map():
            print("Hello, world!")

        cli.add_typer(cmd, name="mapboard", rich_help_panel="Subsystems")
