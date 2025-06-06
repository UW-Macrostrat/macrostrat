"""Basic tests that the CLI runs without crashing."""

from pathlib import Path

from psycopg2.sql import Identifier
from pytest import mark
from typer.testing import CliRunner

from macrostrat.core.migrations import _run_migrations_in_database
from macrostrat.utils import override_environment

runner = CliRunner()

__here__ = Path(__file__).parent


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


@mark.docker
def test_database_migrations(db):
    """Test that database migrations can be run."""

    res = _run_migrations_in_database(db, legacy=False)

    assert res.n_migrations > 0
    assert res.n_remaining == 0


def test_maps_tables_exist(db):
    """Test that the tables exist in the database."""

    for table in ["polygons", "lines", "points"]:
        res = db.run_query(
            "SELECT * FROM {table}", dict(table=Identifier("maps", table))
        ).all()

        assert len(res) == 0
