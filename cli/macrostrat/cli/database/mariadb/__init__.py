from pathlib import Path
from sys import stdin

from sqlalchemy.engine.url import URL
from typer import Argument, Context, Typer

from macrostrat.utils.shell import run

from ..utils import docker_internal_url
from .postgresql_migration import migrate_mariadb_to_postgresql
from .restore import dump_mariadb, restore_mariadb
from .utils import build_connection_args, mariadb_engine

app = Typer(no_args_is_help=True)

mariadb_container = "mariadb:10.10"

# TODO: Adjust Typer context to ignore unconsumed arguments or arguments after "--"


@app.command(
    name="cli",
    add_help_option=False,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def cli_command(ctx: Context):
    """Run the MariaDB CLI against the Macrostrat database."""
    from macrostrat.core.config import mysql_database

    _database: URL = docker_internal_url(mysql_database)

    flags = [
        "-i",
        "--rm",
    ]

    if len(ctx.args) == 0 and stdin.isatty():
        flags.append("-t")

    run(
        "docker",
        "run",
        *flags,
        mariadb_container,
        "mariadb",
        *build_connection_args(_database),
        *ctx.args,
    )


@app.command(
    "dump",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def dump_command(
    ctx: Context,
    output: Path = Argument(None, help="Path to the dump file"),
    database: str = Argument(None, help="Database to dump"),
):
    """Dump a MariaDB database to a file."""
    engine = mariadb_engine(database)

    if output is None:
        output = Path("/dev/stdout")

    dump_mariadb(engine, output, *ctx.args, container=mariadb_container)


@app.command("restore")
def restore_command(
    input: str = Argument(None, help="Path to the dump file or stream"),
    database: str = Argument(None, help="Database to restore to"),
    *,
    create: bool = False,
    overwrite: bool = False,
):
    """Restore a MariaDB database from a dump file or stream."""
    engine = mariadb_engine(database)

    restore_mariadb(
        input,
        engine,
        create=create,
        overwrite=overwrite,
        container=mariadb_container,
    )


app.command("migrate-to-postgres")(migrate_mariadb_to_postgresql)
