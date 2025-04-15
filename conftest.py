"""Basic tests that the CLI runs without crashing."""

import importlib
from pathlib import Path

import docker
from pytest import fixture
from typer.testing import CliRunner

from macrostrat.database import Database
from macrostrat.dinosaur.upgrade_cluster import database_cluster
from macrostrat.utils import override_environment

runner = CliRunner()

__here__ = Path(__file__).parent


@fixture(scope="session")
def cfg():
    cfg_file = __here__ / "cli" / "tests" / "macrostrat.test.toml"
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
