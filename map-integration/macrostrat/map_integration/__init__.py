import os

os.environ["USE_PYGEOS"] = "0"

from macrostrat.database import Database
from typer import Typer
from typer.core import TyperGroup

from macrostrat.core import app

from .commands.copy_to_maps import copy_to_maps
from .commands.ingest import ingest_map
from .commands.match_names import match_names
from .commands.prepare_fields import prepare_fields
from .commands.rgeom import create_rgeom, create_webgeom
from .commands.sources import map_sources
from .migrations import run_migrations


class NaturalOrderGroup(TyperGroup):
    """Allow listing commands in the order they are added."""

    def list_commands(self, ctx):
        return self.commands.keys()


class IngestionCLI(Typer):
    """Command-line application to set up working tables for map ingestion. This is
    designed to be run in an independent database from the main Macrostrat database.
    It is not designed to handle integration, matching, or harmonization tasks."""

    def __init__(self, **kwargs):
        super().__init__(cls=NaturalOrderGroup, **kwargs)

    def add_command(self, func, **kwargs):
        self.command(**kwargs)(func)


app = IngestionCLI(no_args_is_help=True, add_completion=False, name="map-ingestion")

app.add_command(map_sources, name="sources")


# TODO: integrate this migration command with the main database migrations
def _run_migrations(database: str = None):
    """Run migrations to convert a Macrostrat v1 sources table to v2 format."""
    from .database import db

    database_url = db.engine.url
    _db = db
    if database is not None:
        if database.startswith("postgres") and "//" in database:
            database_url = database
        else:
            database_url = database_url.set(database=database)
        _db = Database(database_url)

    print(f"Running migrations on {database_url}")

    run_migrations(_db)


app.add_command(_run_migrations, name="migrate")
app.add_command(ingest_map, name="ingest")
app.add_command(prepare_fields, name="prepare-fields")

# Pass along other arguments to the match-names command
app.add_command(match_names, name="match-names")

app.add_command(create_rgeom, name="create-rgeom")

app.add_command(create_webgeom, name="create-webgeom")

app.add_command(copy_to_maps, name="insert")
