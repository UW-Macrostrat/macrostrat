"""Basic tests that the CLI runs without crashing."""

import importlib
from pathlib import Path

import docker
from macrostrat.database import Database
from macrostrat.dinosaur.upgrade_cluster import database_cluster
from macrostrat.utils import override_environment, get_logger
from pytest import fixture, skip
from typer.testing import CliRunner

runner = CliRunner()

log = get_logger(__name__)

__here__ = Path(__file__).parent


def pytest_addoption(parser):
    parser.addoption(
        "--skip-database",
        action="store_true",
        default=False,
        help="skip database tests",
    )

    parser.addoption(
        "--skip-env",
        action="store_true",
        default=False,
        help="skip env tests",
    )

    parser.addoption(
        "--env", action="store", default=None, help="override the environment"
    )


# We have to do some complicated stuff to import two separate versions
# of the config module.
module_spec = importlib.util.find_spec("macrostrat.core.config")


@fixture(scope="session")
def env_config(request):
    """
    Load the config for the current environment. This allows integration tests to be run.
    These tests may assume the presence of data in the database.
    """
    if request.config.getoption("--skip-env"):
        skip("skipping environment tests")

    kwargs = {
        "NO_COLOR": "1",
    }
    env = request.config.getoption("--env")
    if env is not None:
        log.info("Overriding environment to %s", env)
        kwargs["MACROSTRAT_ENV"] = env

    with override_environment(**kwargs):
        mod_instance = load_config_module()
        # Print the current environment to the PyTest output
        log.info("Current env: %s", mod_instance.settings.env)

        yield mod_instance.settings


## TODO: labeled databases with expected environments where tests will succeed.
# This will allow us to flexibly define which tests should pass with different
# data loaded into the Macrostrat database. Tests could be runnable on dev, staging,
# prod, or empty databases as needed.


# TODO: ensure that tests on "live" environments are read-only by connecting to a read-only user.
@fixture(scope="session")
def db(env_config):
    """The actually operational database for the current environment."""

    if env_config is None:
        skip("No environment configured")

    if env_config.pg_database is None:
        skip("No database configured for this environment")

    db = Database(env_config.pg_database)
    # Change the user on the connection
    # db.run_sql("SET ROLE macrostrat_reader;")

    yield db


def load_config_module():
    mod_instance = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(mod_instance)
    return mod_instance


@fixture()
def cfg():
    cfg_file = __here__ / "cli" / "tests" / "macrostrat.test.toml"
    with override_environment(MACROSTRAT_CONFIG=str(cfg_file), NO_COLOR="1"):
        mod_instance = load_config_module()

        assert cfg_file == mod_instance.settings.config_file
        yield mod_instance.settings


@fixture(scope="session")
def test_db(request):
    """A temporary, initially empty database for Macorstrat testing."""
    # Get the current settings without an override
    cfg = load_config_module().settings
    if request.config.getoption("--skip-database"):
        import pytest

        pytest.skip("skipping database tests")

    # Spin up a docker container with a temporary database using the
    # pg_database_container image

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
