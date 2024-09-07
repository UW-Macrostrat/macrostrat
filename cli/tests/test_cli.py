"""Basic tests that the CLI runs without crashing."""

from pathlib import Path

import typer.core
from typer.testing import CliRunner

from macrostrat.utils import override_environment

typer.core.rich = True

runner = CliRunner()

__here__ = Path(__file__).parent


def test_cli_help():
    cfg_file = __here__ / "macrostrat.test.toml"
    with override_environment(MACROSTRAT_CONFIG=str(cfg_file), NO_COLOR="1"):
        from macrostrat.cli import main
        from macrostrat.core.config import settings

        assert cfg_file == settings.config_file

        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "Macrostrat control interface" in result.output


def test_cli_database():
    cfg_file = __here__ / "macrostrat.test.toml"
    with override_environment(MACROSTRAT_CONFIG=str(cfg_file), NO_COLOR="1"):
        from macrostrat.core.config import settings

        assert (
            settings.pg_database
            == "postgresql://user:password@localhost:5432/macrostrat"
        )


def test_cli_no_config():
    with override_environment(MACROSTRAT_CONFIG="", NO_COLOR="1"):
        from macrostrat.cli import main

        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "Macrostrat control interface" in result.output
        assert "Active environment: None" in result.output
