import os

os.environ["USE_PYGEOS"] = "0"

from typer import Typer
from typer.core import TyperGroup
import sys
from .commands.ingest import ingest_map
from .commands.homogenize import prepare_fields
from .commands.match_names import match_names
from .commands.sources import map_sources
from .commands.rgeom import create_rgeom, create_webgeom

from .database import db, create_fixtures
from .migrations import run_migrations


class NaturalOrderGroup(TyperGroup):
    """Allow listing commands in the order they are added."""

    def list_commands(self, ctx):
        return self.commands.keys()


class IngestionCLI(Typer):
    def __init__(self, **kwargs):
        super().__init__(cls=NaturalOrderGroup, **kwargs)

    def add_command(self, func, **kwargs):
        self.command(**kwargs)(func)


app = IngestionCLI(no_args_is_help=True, add_completion=False, name="map-ingestion")

app.add_command(create_fixtures, name="create-fixtures")
app.add_command(map_sources, name="sources")

app.add_command(run_migrations, name="migrate")


app.add_command(ingest_map, name="ingest")

app.add_command(prepare_fields, name="prepare-fields")

# Pass along other arguments to the match-names command
app.add_command(match_names, name="match-names")


app.add_command(create_rgeom, name="create-rgeom")

app.add_command(create_webgeom, name="create-webgeom")
