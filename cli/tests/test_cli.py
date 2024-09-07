"""Basic tests that the CLI runs without crashing."""

from typer.testing import CliRunner

from macrostrat.cli import main
from pathlib import Path
from macrostrat.utils import override_environment

runner = CliRunner()

__here__ = Path(__file__).parent


def test_cli_help():
    cfg_file = __here__ / "macrostrat.test.toml"
    with override_environment(MACROSTRAT_CONFIG=str(cfg_file)):
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "Macrostrat control interface" in result.output


def test_cli_no_config():
    with override_environment(MACROSTRAT_CONFIG=""):
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "Macrostrat control interface" in result.output
        assert "Active environment: None" in result.output
