import os

from typer import Typer, Context
from sys import stdin
from macrostrat.utils.shell import run
from sqlalchemy.engine.url import URL

from .utils import build_connection_args

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
