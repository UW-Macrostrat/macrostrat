from pathlib import Path

from macrostrat.core.config import settings
from pytest import main
from typer import Typer

# TODO: Rework using pytest

cli = Typer(
    short_help="The testing suite",
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
