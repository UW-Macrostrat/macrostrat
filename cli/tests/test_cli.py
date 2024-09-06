"""Basic tests that the CLI runs without crashing."""

from typer.testing import CliRunner

from macrostrat.cli import main

runner = CliRunner()


def test_cli_help():
    with runner.isolated_filesystem():
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "Macrostrat control interface" in result.output
