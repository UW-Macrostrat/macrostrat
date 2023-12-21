from typer.testing import CliRunner
from os import environ
from unittest import mock

from .cli import main

runner = CliRunner()


def test_app():
    """Test that the CLI app runs"""
    result = runner.invoke(main)
    assert result.exit_code == 0


@mock.patch.dict(environ, {"MACROSTRAT_ENV": "invalid-env"})
def test_invalid_env():
    """Test that we can override environment variables"""
    result = runner.invoke(main, "env")
    assert result.exit_code != 0
