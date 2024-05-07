import os

os.environ["USE_PYGEOS"] = "0"

from sys import stdin

from macrostrat.core import app
from macrostrat.database import Database
from psycopg2.sql import Identifier
from typer import Argument, Option, Typer
from typer.core import TyperGroup

from .commands.copy_sources import copy_macrostrat_sources
from .commands.fix_geometries import fix_geometries
from .commands.ingest import ingest_map
from .commands.prepare_fields import prepare_fields
from .commands.set_srid import apply_srid
from .commands.source_info import source_info
from .commands.sources import map_sources
from .migrations import run_migrations
from .pipeline import ingest_file, ingest_from_csv, ingest_object, run_polling_loop
from .process import cli as _process
from .utils import IngestionCLI, MapInfo

help_text = f"""Ingest maps into Macrostrat.

Active map: [bold cyan]{app.state.get("active_map")}[/]
"""

cli = IngestionCLI(no_args_is_help=True, name="map-ingestion", help=help_text)


@cli.command(name="set-active")
def set_active_map(map: MapInfo = None):
    """Set the active map for the current session."""
    if map is None:
        app.console.print("Clearing active map")
    else:
        app.console.print(f"Setting active map to [item]{map.slug}")
    app.state.set("active_map", map.slug)


cli.add_command(ingest_map, name="ingest")
cli.add_command(prepare_fields, name="prepare-fields")
cli.add_command(fix_geometries, name="fix-geometries")
cli.add_command(apply_srid, name="apply-srid")

cli.add_command(ingest_file, name="ingest-file")
cli.add_command(ingest_from_csv, name="ingest-from-csv")
cli.add_command(ingest_object, name="ingest-object")
cli.add_command(run_polling_loop, name="run-polling-loop")

cli.add_typer(_process, name="process")

cli.add_command(source_info, name="info")


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


sources.add_command(_run_migrations, name="migrate-schema")


cli.add_typer(sources, name="sources", help="Manage map sources")
