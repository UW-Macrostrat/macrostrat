from typer import Typer
from typer.core import TyperGroup


class NaturalOrderGroup(TyperGroup):
    """Allow listing commands in the order they are added."""

    def list_commands(self, ctx):
        return self.commands.keys()


class IngestionCLI(Typer):
    """Command-line application to set up working tables for map ingestion. This is
    designed to be run in an independent database from the main Macrostrat database.
    It is not designed to handle integration, matching, or harmonization tasks."""

    def __init__(self, **kwargs):
        super().__init__(cls=NaturalOrderGroup, rich_markup_mode="rich", **kwargs)

    def add_command(self, func, **kwargs):
        self.command(**kwargs)(func)
