"""Basic tests that the CLI runs without crashing."""

import importlib
from os import environ
from pathlib import Path

from pytest import fixture, mark, skip
from typer.testing import CliRunner

from macrostrat.database import Database
from macrostrat.schema_management.defs import test_database_cluster
from macrostrat.utils import get_logger, override_environment

runner = CliRunner()

log = get_logger(__name__)

__here__ = Path(__file__).parent


def pytest_addoption(parser):
    parser.addoption(
        "--skip-database",
        action="store_true",
        default=False,
        help="skip local database creation",
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

    parser.addoption(
        "--optimize-database",
        action="store_true",
        default=True,
        help="optimize database for fast testing",
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
def env_db(env_config):
    """The actually operational database for the current environment."""

    if env_config is None:
        skip("No environment configured")

    if env_config.pg_database is None:
        skip("No database configured for this environment")

    db = Database(env_config.pg_database)

    # Change the user on the connection to a read-only user
    # TODO: verify read-only
    db.run_sql("SET ROLE web_anon;")

    yield db


@fixture(scope="class")
def db(env_db):
    with env_db.transaction(rollback=True):
        yield env_db


def load_config_module():
    mod_instance = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(mod_instance)
    return mod_instance


@fixture(scope="session")
def empty_db(request):
    """A temporary, initially empty database for Macorstrat testing."""
    # Get the current settings without an override
    if request.config.getoption("--skip-database"):
        skip("skipping Docker test database")

    optimize = request.config.getoption("--optimize-database")

    with test_database_cluster(username="macrostrat_admin", optimize=optimize) as db:
        yield db


@fixture(scope="session")
def test_db(request, empty_db: Database):
    """The database used for testing."""
    from macrostrat.core.config import settings
    from macrostrat.schema_management import apply_schema_for_environment

    _filter = lambda s, p: True

    if request.config.getoption("--optimize-database"):
        # If we're optimizing the database, we want to skip any statements that are not necessary for testing.
        # This is a bit hacky, but it allows us to significantly speed up the tests by skipping things like
        # indexes, constraints, and permissions that are not necessary for mist tests.
        def _filter(statement: str, path: Path):
            stmt = statement.strip().lower()
            if (
                stmt.startswith("create index")
                or stmt.startswith("create unique index")
                or statement.startswith("alter index")
            ):
                return False

            # Modify ownership of tables
            if stmt.startswith("alter table") and "owner to" in stmt:
                return False

            if stmt.startswith("grant"):
                return False

            return True

    apply_schema_for_environment(
        empty_db,
        env=settings.environment,
        statement_filter=_filter,
    )
    return empty_db
