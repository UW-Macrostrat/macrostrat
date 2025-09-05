"""
Scripts to assist with running various services against different environments.
"""

from os import environ

from macrostrat.utils import working_directory, cmd
from typer import Typer

from macrostrat.core.config import settings
from macrostrat.core.console import err_console

dev_app = Typer(help="Run services in development", no_args_is_help=True)


@dev_app.command("api-v3")
def run_api_v3():
    """Run the API v3 service."""

    v3_root = settings.srcroot / "services" / "api-v3"

    # Prepare environment
    environ["uri"] = settings.pg_database

    err_console.print(
        f"Running [bold]API v3[/bold] service in environment [bold]{settings.env}[/bold]..."
    )

    # Print warnings
    err_console.print(
        "Running [bold]API v3[/bold] locally does not currently support authentication.",
        style="warning",
    )

    # Change to the service directory
    with working_directory(v3_root):
        # Run the service
        cmd("make")
