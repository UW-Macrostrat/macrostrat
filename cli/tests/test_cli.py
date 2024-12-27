"""Basic tests that the CLI runs without crashing."""

from pathlib import Path

from macrostrat.utils import override_environment
from pytest import fixture, mark
from typer.testing import CliRunner

runner = CliRunner()

__here__ = Path(__file__).parent


@fixture
def cfg():
    cfg_file = __here__ / "macrostrat.test.toml"
    with override_environment(MACROSTRAT_CONFIG=str(cfg_file), NO_COLOR="1"):
        from macrostrat.core.config import settings

        assert cfg_file == settings.config_file
        yield settings


def test_cli_help(cfg):
    from macrostrat.cli import main

    result = runner.invoke(main, [])
    assert result.exit_code == 0


def test_cli_database(cfg):
    assert cfg.pg_database == "postgresql://user:password@localhost:5432/macrostrat"


def test_cli_no_config():
    with override_environment(MACROSTRAT_CONFIG="", NO_COLOR="1"):
        from macrostrat.cli import main

        result = runner.invoke(main, [])
        assert result.exit_code == 0
        # assert "Macrostrat control interface" in result.output
        # assert "Active environment: None" in result.output


@mark("migrations")
def test_database_migrations(cfg):
    from macrostrat.core.migrations import _dry_run_migrations

    res = _dry_run_migrations(legacy=False)

    assert res.n_migrations > 0
    assert res.n_remaining == 0
