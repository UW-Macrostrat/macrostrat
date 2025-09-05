"""
Basic wrapper for PyTest to run Macrostrat tests.

"""

from pathlib import Path

from pytest import main
from typer import Typer, Context

from macrostrat.core.config import settings

cli = Typer(
    short_help="Macrostrat tests",
    no_args_is_help=True,
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


@cli.command(
    name="all",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def all_tests(ctx: Context) -> None:
    # run the banana command with all arguments
    """Run all tests"""
    main(
        [
            settings.srcroot / "cli",
            settings.srcroot / "py-modules",
            settings.srcroot / "map-integration",
            *ctx.args,
        ]
    )


@cli.command(name="quick")
def unit_tests(ctx: Context) -> None:
    """Run quick tests that skip the database"""
    ctx.args += ["--skip-test-database", "--disable-warnings"]
    all_tests(ctx)
