from pathlib import Path

from pytest import main
from typer import Typer

from macrostrat.core.config import settings

cli = Typer(
    short_help="Macrostrat tests",
    no_args_is_help=True,
    add_completion=False,
)

__here__ = Path(__file__).parent


@cli.command(name="runtime")
def runtime_tests():
    """Test the deployed application"""
    print("Running runtime tests")

    main(["-v", settings.srcroot / "runtime-tests"])


@cli.command(name="cli")
def cli_tests():
    """Test the CLI"""
    print("Running CLI tests")

    main(["-v", settings.srcroot / "cli" / "tests"])
