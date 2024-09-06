"""Basic tests that the CLI runs without crashing."""

from typer.testing import CliRunner

from macrostrat.cli import main

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Macrostrat CLI" in result.output
