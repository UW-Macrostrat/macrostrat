"""Basic tests that the CLI runs without crashing."""

import importlib
from pathlib import Path

from pytest import fixture, mark, skip
from typer.testing import CliRunner

from macrostrat.database import Database
from macrostrat.utils import get_logger, override_environment

from macrostrat.schema_management.defs import test_database_cluster
from sqlalchemy.orm import Session


runner = CliRunner()

log = get_logger(__name__)

__here__ = Path(__file__).parent


def pytest_addoption(parser):
    parser.addoption(
        "--skip-test-database",
        action="store_true",
        default=False,
        help="skip test database creation",
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

    parser.addoption(
        "--skip-slow",
        action="store_true",
        default=False,
        help="skip slow tests",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--skip-slow"):
        skip_slow_marker = mark.skip(reason="skipping slow tests")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow_marker)


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
def base_db(env_config):
    """The actually operational database for the current environment."""

    if env_config is None:
        skip("No environment configured")

    if env_config.pg_database is None:
        skip("No database configured for this environment")

    db = Database(env_config.pg_database)
    # Change the user on the connection
    db.run_sql("SET ROLE web_anon;")

    yield db


@fixture(scope="class")
def db(base_db):
    with base_db.transaction(rollback=True):
        yield base_db


def load_config_module():
    mod_instance = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(mod_instance)
    return mod_instance


from testcontainers.postgres import PostgresContainer


@fixture(scope="session")
def empty_db(request):
    """A temporary, initially empty database for Macorstrat testing."""
    # Get the current settings without an override
    if request.config.getoption("--skip-test-database"):
        import pytest

        pytest.skip("skipping Docker test database")

    with test_database_cluster() as db:
        yield db


@fixture(scope="session")
def temp_db(empty_db: Database):
    """The database used for testing."""
    from macrostrat.schema_management import apply_schema_for_environment
    from macrostrat.core.config import settings

    apply_schema_for_environment(empty_db, env=settings.environment)
    return empty_db
