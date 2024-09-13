from pathlib import Path

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
    main(["-v", __here__])
