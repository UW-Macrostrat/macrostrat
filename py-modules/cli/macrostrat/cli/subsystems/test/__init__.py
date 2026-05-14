"""
Basic wrapper for PyTest to run Macrostrat tests.

"""

from pathlib import Path
from typer import Context, Typer

from macrostrat.core.config import settings
from macrostrat.utils import working_directory

cli = Typer(
    short_help="Macrostrat tests",
    add_completion=False,
    help="""
    Run Macrostrat tests.

    Custom options:
    --skip-test-database: skip Docker database tests
    --skip-env: skip environment tests
                necessary when you don't have a connection to an active environment
    --env: override the environment
    """,
)

__here__ = Path(__file__).parent


def run_pytest(args):
    from pytest import main

    res = main(args)
    if res != 0:
        raise SystemExit(res)


@cli.command(name="runtime")
def runtime_tests():
    """Test the deployed application"""
    print("Running runtime tests")

    run_pytest(["-v", settings.srcroot / "runtime-tests"])


@cli.command(name="cli")
def cli_tests():
    """Test the CLI"""
    print("Running CLI tests")

    run_pytest(["-v", settings.srcroot / "cli" / "tests"])


@cli.command(
    name="all",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def all_tests(ctx: Context, quick: bool = False) -> None:
    """Run all tests"""
    with working_directory(settings.srcroot):
        args = ctx.args
        if quick:
            args += ["--skip-slow", "--failed-first", "-x", "--show-capture=no"]
        run_pytest(args)


@cli.command(
    name="quick",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def unit_tests(ctx: Context) -> None:
    """Run quick tests that skip the database"""
    ctx.args += ["--skip-test-database", "--disable-warnings", "--skip-slow"]
    all_tests(ctx)
