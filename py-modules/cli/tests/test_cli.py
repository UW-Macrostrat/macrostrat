"""Basic tests that the CLI runs without crashing."""

import importlib
from pathlib import Path

from psycopg.sql import Identifier
from pytest import fixture, mark
from typer.testing import CliRunner

from macrostrat.schema_management.migrations import (
    _run_migrations_in_database,
    ReadinessState,
)
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


def test_cli_help(test_cfg):
    from macrostrat.cli.entrypoint import main

    result = runner.invoke(main, [])
    assert result.exit_code == 0


def test_cli_database(test_cfg):
    assert (
        test_cfg.pg_database == "postgresql://user:password@localhost:5432/macrostrat"
    )


def test_cli_no_config():
    with override_environment(MACROSTRAT_CONFIG="", NO_COLOR="1"):
        from macrostrat.cli.entrypoint import main

        result = runner.invoke(main, [])
        assert result.exit_code == 0
        # assert "Macrostrat control interface" in result.output
        # assert "Active environment: None" in result.output


@mark.docker
def test_database_migrations(test_db_base):
    """Test that no database migrations are needed to reach the optimal database state."""

    # NOTE: we need to use readiness_level=ReadinessState.GA here because when running
    # in CI, we don't preload the development schema adjustments. We could potentially change
    # this.
    res = _run_migrations_in_database(
        test_db_base, legacy=False, raise_errors=True, readiness_level=ReadinessState.GA
    )
    assert res.n_migrations == 0
    assert res.n_remaining == 0


def test_maps_tables_exist(test_db_full):
    """Test that the tables exist in the database."""

    for table in ["polygons", "lines", "points"]:
        res = test_db_full.run_query(
            "SELECT * FROM {table}", dict(table=Identifier("maps", table))
        ).all()

        assert len(res) == 0
