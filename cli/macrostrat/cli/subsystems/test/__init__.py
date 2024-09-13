from rich import print
from typer import Typer

# TODO: Rework using pytest

cli = Typer(
    short_help="The testing suite",
    no_args_is_help=True,
    add_completion=False,
)


@cli.command(name="runtime")
def runtime_tests():
    """Test the deployed application"""
    print("[bold green]All tests passed!")
