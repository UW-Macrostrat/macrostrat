"""The `macrostrat schema` commands.

The general system is `macrostrat.schema_management`; this module holds what is
Macrostrat's own: its chunks, where its migrations live, and two utilities.
"""

import asyncio
from sys import exit, stderr

from rich import print
from typer import Argument

from macrostrat.core.config import settings
from macrostrat.core.database import engine_for_db_name, get_database
from macrostrat.database.transfer import pg_dump_to_file
from macrostrat.schema_management.cli import create_schema_cli
from macrostrat.utils.shell import run

from .app import schema_definition

schema_app = create_schema_cli(schema_definition)


@schema_app.command(name="scripts", rich_help_panel="Utils")
def run_scripts(migration: str = Argument(None)):
    """Run ad-hoc data management scripts

    These will be integrated with the migration system in the future.
    """
    pth = settings.srcroot / "schema" / "_data_scripts"
    files = list(pth.glob("*.sql")) + list(pth.glob("*.sh")) + list(pth.glob("*.py"))
    files.sort()
    if migration is None:
        print("[yellow bold]No script specified\n", file=stderr)
        print("[bold]Available scripts:", file=stderr)
        for f in files:
            print(f"  {f.stem}[dim]{f.suffix}", file=stderr)
        exit(1)
    matching_migrations = [
        f for f in files if f.stem == migration or str(f) == migration
    ]
    if len(matching_migrations) == 0:
        print(f"Script {migration} does not exist", file=stderr)
        exit(1)
    if len(matching_migrations) > 1:
        print(f"Ambiguous script name: {migration}", file=stderr)
        print("Please specify the full file name")
        exit(1)
    migration = matching_migrations[0]
    if migration.suffix == ".py":
        run("python", str(migration))
    if migration.suffix == ".sh":
        run(str(migration))
    if migration.suffix == ".sql":
        db = get_database()
        db.run_sql(migration)


@schema_app.command("dump", rich_help_panel="Utils")
def dump_schema(schema: str):
    """Dump managed schemas using [cyan]pg_dump[/]"""
    engine = engine_for_db_name("macrostrat")
    dumpfile = settings.srcroot / "schema" / str(settings.env) / f"0999-{schema}.sql"
    print(f"[dim]Dumping schema [bold cyan]{schema}[/] to [bold]{dumpfile}[/]")
    task = pg_dump_to_file(
        engine,
        dumpfile,
        custom_format=False,
        args=["--schema-only", "--schema", schema],
    )
    asyncio.run(task)
