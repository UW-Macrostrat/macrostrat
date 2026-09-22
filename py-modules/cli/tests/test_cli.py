"""Basic tests that the CLI runs without crashing."""

import importlib
import re
from os import getenv
from pathlib import Path

from click.exceptions import NoArgsIsHelpError
from pytest import fixture
from typer.testing import CliRunner

from macrostrat.utils import override_environment


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


runner = CliRunner()

__here__ = Path(__file__).parent

test_cfg_file = __here__ / "macrostrat.test.toml"


@fixture(scope="module")
def test_cfg():
    import macrostrat.core.config as cfg

    try:
        with override_environment(
            MACROSTRAT_CONFIG=str(test_cfg_file.resolve()),
            MACROSTRAT_ENV="development",
            NO_COLOR="1",
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


def test_cli_cfg_file(test_cfg):
    """Test that the proper config file is loaded."""
    assert test_cfg.config_file == test_cfg_file.resolve()


def test_cli_help(test_cfg):
    from macrostrat.cli.entrypoint import main

    result = runner.invoke(main, [], catch_exceptions=False)
    assert is_default_cli_help(result)


def test_cli_database(test_cfg):
    """Test that a database string configuration is passed through successfully."""
    assert (
        test_cfg.pg_database == "postgresql://user:password@localhost:5432/macrostrat"
    )


def test_cli_no_config():
    import macrostrat.cli.entrypoint as cli_entry
    import macrostrat.core as core
    import macrostrat.core.config as cfg
    import macrostrat.core.main as main

    with override_environment(
        MACROSTRAT_CONFIG="", NO_COLOR="1", MACROSTRAT_ENV="", FORCE_COLOR=""
    ):
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
        plain_output = strip_ansi(result.output)
        assert "Macrostrat control interface" in plain_output
        assert "Active environment: None" in plain_output


v2_cfg_file = __here__ / "macrostrat.v2.test.toml"


def test_cli_config_version_2():
    """A file declaring config_version = 2 is read by the schema loader.

    The same `settings` surface comes back — the legacy `pg_database` reading,
    the ambient PG* export for a literal login — so nothing downstream notices.
    """
    from os import environ

    import macrostrat.core.config as cfg

    try:
        with override_environment(
            MACROSTRAT_CONFIG=str(v2_cfg_file.resolve()),
            MACROSTRAT_ENV="local",
            MACROSTRAT_CONFIG_VERSION="",
            NO_COLOR="1",
        ):
            importlib.reload(cfg)
            settings = cfg.settings
            assert cfg.IS_V2
            assert type(settings).__name__ == "MacrostratSettings"
            assert settings.env == "local"
            assert settings.config_file == v2_cfg_file.resolve()
            assert settings.pg_database == (
                "postgresql://user:password@localhost:5432/macrostrat"
            )
            assert settings.databases["test"].endswith("/macrostrat_test")
            assert settings.get("pg_database_container") == "imresamu/postgis:15-3.4"
            assert settings.policy.env_class.value == "local"
            # A literal login still exports the ambient variables.
            assert environ.get("PGPASSWORD") == "password"
            assert environ.get("SECRET_KEY") == "test-signing-key"
    finally:
        importlib.reload(cfg)
