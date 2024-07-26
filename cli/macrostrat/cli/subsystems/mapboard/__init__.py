from macrostrat.core import MacrostratSubsystem


class MapboardSubsystem(MacrostratSubsystem):
    name = "mapboard"

    def on_add_commands(self, cli):
        @cli.command("export-mapboard", rich_help_panel="Export")
        def export_map():
            print("Hello, world!")

        cli.add_typer(self.control_command(), rich_help_panel="Subsystems")
