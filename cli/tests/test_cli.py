"""Basic tests that the CLI runs without crashing."""

import importlib
from pathlib import Path

import docker
from macrostrat.database import Database
from macrostrat.dinosaur.upgrade_cluster import database_cluster
from macrostrat.utils import override_environment
from pytest import fixture, mark
from typer.testing import CliRunner

from macrostrat.core.migrations import _run_migrations_in_database

runner = CliRunner()

__here__ = Path(__file__).parent


@fixture(scope="session")
def cfg():
    cfg_file = __here__ / "macrostrat.test.toml"
    with override_environment(MACROSTRAT_CONFIG=str(cfg_file), NO_COLOR="1"):
        importlib.reload(importlib.import_module("macrostrat.core.config"))
        from macrostrat.core.config import settings

        assert cfg_file == settings.config_file
        yield settings


@fixture(scope="session")
def db(cfg):
    # Spin up a docker container with a temporary database
    image = cfg.get("pg_database_container", "postgres:15")

    client = docker.from_env()

    img_root = cfg.srcroot / "base-images" / "database"

    # Build postgres pgaudit image
    img_tag = "macrostrat-local-database:latest"

    client.images.build(path=str(img_root), tag=img_tag)

    # Spin up an image with this container
    port = 54884
    with database_cluster(client, img_tag, port=port) as container:
        url = f"postgresql://postgres@localhost:{port}/postgres"
        db = Database(url)
        yield db


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
