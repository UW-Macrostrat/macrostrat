import os

os.environ["USE_PYGEOS"] = "0"

from sys import stdin

from macrostrat.database import Database
from psycopg2.sql import Identifier
from typer import Argument, Option, Typer
from typer.core import TyperGroup

from macrostrat.core import app

from .commands.copy_sources import copy_macrostrat_sources
from .commands.copy_to_maps import copy_to_maps
from .commands.ingest import ingest_map
from .commands.match_names import match_names
from .commands.prepare_fields import prepare_fields
from .commands.process.rgeom import create_rgeom, create_webgeom
from .commands.source_info import source_info
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


app.add_command(ingest_map, name="ingest")
app.add_command(prepare_fields, name="prepare-fields")

# Pass along other arguments to the match-names command
app.add_command(match_names, name="match-names")

app.add_command(create_rgeom, name="create-rgeom")

app.add_command(create_webgeom, name="create-webgeom")
app.add_command(copy_to_maps, name="insert")

sources = IngestionCLI(no_args_is_help=True)
sources.add_command(copy_macrostrat_sources, name="copy")
sources.add_command(map_sources, name="list")


@sources.command(name="delete")
def delete_sources(
    slugs: list[str],
    dry_run: bool = Option(False, "--dry-run"),
):
    """Delete sources from the map ingestion database."""
    from .database import db

    if not stdin.isatty() and len(slugs) == 1 and slugs[0] == "-":
        slugs = [line.strip() for line in stdin]

    if dry_run:
        print("Deleting maps:")
        print("  " + "\n  ".join(slugs))

        print("\nDry run; not actually deleting anything")
        return

    for slug in slugs:
        print(f"Deleting map {slug}")
        print(slug)
        tables = db.run_query(
            "SELECT primary_table, primary_line_table FROM maps.sources WHERE slug = :slug",
            dict(slug=slug),
        ).fetchone()

        line_table = None
        poly_table = None
        if tables is not None:
            line_table = tables.primary_line_table
            poly_table = tables.primary_table

        if line_table is None:
            line_table = f"{slug}_lines"
        if poly_table is None:
            poly_table = f"{slug}_polygons"
        points_table = f"{slug}_points"

        for table in [line_table, poly_table, points_table]:
            db.run_sql(
                "DROP TABLE IF EXISTS {table}",
                dict(table=Identifier("sources", table)),
            )

        db.run_sql("DELETE FROM maps.sources WHERE slug = :slug", dict(slug=slug))


sources.add_command(_run_migrations, name="migrate-schema")

sources.add_command(source_info, name="info")

app.add_typer(sources, name="sources", help="Manage map sources")
