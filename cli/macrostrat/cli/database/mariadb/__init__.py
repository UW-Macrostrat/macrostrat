from typer import Typer, Context, Argument
from sys import stdin
from macrostrat.utils.shell import run
from sqlalchemy.engine import create_engine
from sqlalchemy.engine.url import URL, make_url
from pathlib import Path

from .utils import build_connection_args
from .restore import restore_mariadb

app = Typer(no_args_is_help=True)

mariadb_container = "mariadb:10.10"


@app.command(
    name="cli",
    add_help_option=False,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def cli_command(ctx: Context):
    """Run the MariaDB CLI against the Macrostrat database."""
    from macrostrat.core.config import docker_internal_url, mysql_database

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


@app.command("restore")
def restore_command(
    input: str = Argument(None, help="Path to the dump file or stream"),
    *,
    create: bool = False,
    overwrite: bool = False,
):
    """Restore a MariaDB database from a dump file or stream."""
    from macrostrat.core.config import mysql_database

    _database: URL = make_url(mysql_database)
    _database = _database.set(drivername="mysql+pymysql")

    restore_mariadb(
        input,
        create_engine(_database),
        create=create,
        overwrite=overwrite,
        container=mariadb_container,
    )
