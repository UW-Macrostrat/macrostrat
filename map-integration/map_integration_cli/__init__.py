import os

os.environ["USE_PYGEOS"] = "0"

from typer import Typer
from typer.core import TyperGroup
import sys
from .commands.ingest import ingest_map
from .commands.homogenize import prepare_fields
from .commands.match_names import match_names
from .commands.sources import map_sources
from .commands.rgeom import create_rgeom

from .database import db


class NaturalOrderGroup(TyperGroup):
    """Allow listing commands in the order they are added."""

    def list_commands(self, ctx):
        return self.commands.keys()


class IngestionCLI(Typer):
    def __init__(self, **kwargs):
        super().__init__(cls=NaturalOrderGroup, **kwargs)

    def add_command(self, func, **kwargs):
        self.command(**kwargs)(func)


app = IngestionCLI(no_args_is_help=True, add_completion=False)
app.add_command(map_sources, name="sources")


app.add_command(ingest_map, name="ingest")

app.add_command(prepare_fields, name="prepare-fields")

# Pass along other arguments to the match-names command
app.add_command(match_names, name="match-names")


app.add_command(create_rgeom, name="create-rgeom")


def main():
    # if len(sys.argv) > 1 and sys.argv[1] == "maps":
    #     sys.argv = sys.argv[1:]
    app()
    # else:
    #     # Fall back to rest of CLI if we're not dealing with maps
    #     # NOTE: this should probably be inverted eventually.
    #     # The map CLI should be a subcommand of the main CLI,
    #     # not the other way around.
    #     try:
    #         from macrostrat_cli.cli import main

    #         main()
    #     except ModuleNotFoundError:
    #         print("macrostrat's main CLI is not installed")
    #         return
