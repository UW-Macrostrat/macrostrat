"""Basic tests that the CLI runs without crashing."""

import importlib
from os import getenv
from pathlib import Path

from click.exceptions import NoArgsIsHelpError
from pytest import fixture
from typer.testing import CliRunner

from macrostrat.utils import override_environment

runner = CliRunner()

__here__ = Path(__file__).parent

test_cfg_file = __here__ / "macrostrat.test.toml"


@fixture(scope="module")
def test_cfg():
    import macrostrat.core.config as cfg

    try:
        with override_environment(
            MACROSTRAT_CONFIG=str(test_cfg_file.resolve()), NO_COLOR="1"
        ):
            importlib.reload(cfg)
            yield cfg.settings
    finally:
        importlib.reload(cfg)


def is_default_cli_help(result):
    """Assert that a CLI invocation with no arguments raises a NoArgsIsHelpError.
    This is a workaround for weird behavior in Typer's test runner
    """
    try:
        assert result.exit_code == 2
        assert isinstance(result.exception, SystemExit)
        # Typer catches NoArgsIsHelpError and raises SystemExit.
        assert isinstance(result.exception.__context__, NoArgsIsHelpError)
        return True
    except AssertionError:
        return False


def test_cli_help(test_cfg):
    from macrostrat.cli.entrypoint import main

    result = runner.invoke(main, [], catch_exceptions=False)
    assert is_default_cli_help(result)


def test_cli_database(test_cfg):
    assert (
        test_cfg.pg_database == "postgresql://user:password@localhost:5432/macrostrat"
    )


def test_cli_no_config():
    import macrostrat.core as core
    import macrostrat.core.config as cfg
    import macrostrat.core.main as main
    import macrostrat.cli.entrypoint as cli_entry

    with override_environment(MACROSTRAT_CONFIG="", NO_COLOR="1", MACROSTRAT_ENV=""):
        # We need to specifically unset the environment variable, not set it to ""

        assert getenv("MACROSTRAT_CONFIG") == ""
        assert getenv("MACROSTRAT_ENV") == ""

        # Reload libraries (order matters!)
        for mod in [cfg, main, core, cli_entry]:
            importlib.reload(mod)

        assert cfg.settings.config_file is None
        assert cfg.settings.env is None

        result = runner.invoke(cli_entry.main, [])

        assert is_default_cli_help(result)
        assert "Macrostrat control interface" in result.output

        did_assert = False
        for line in result.output.splitlines():
            if line.strip().startswith("Active environment:"):
                assert "Active environment: None" in line
                did_assert = True
                break
        assert did_assert
