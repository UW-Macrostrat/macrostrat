"""Basic tests that the CLI runs without crashing."""

import importlib
from pathlib import Path
from typing import Optional

from pytest import fixture, mark, skip
from sqlalchemy import make_url
from typer.testing import CliRunner

from macrostrat.database import Database
from macrostrat.database.query import StatementContext, StatementDirective
from macrostrat.database.utils import temporary_database
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

    parser.addoption(
        "--no-optimize-database",
        action="store_false",
        dest="optimize_database",
        help="do not optimize database for fast testing",
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

    kwargs = {}
    env = request.config.getoption("--env")
    if env is not None:
        log.info("Overriding environment to %s", env)
        kwargs["MACROSTRAT_ENV"] = env

    with override_environment(**kwargs):
        mod_instance = load_config_module()
        # Print the current environment to the PyTest output
        log.info("Current env: %s", mod_instance.settings.env)

        if mod_instance.settings.env is None:
            skip("No environment configured")

        yield mod_instance.settings


## TODO: labeled databases with expected environments where tests will succeed.
# This will allow us to flexibly define which tests should pass with different
# data loaded into the Macrostrat database. Tests could be runnable on dev, staging,
# prod, or empty databases as needed.


# TODO: ensure that tests on "live" environments are read-only by connecting to a read-only user.
@fixture(scope="session")
def env_db(env_config):
    """The actually operational database for the current environment."""
    try:
        log.info("Connecting to environment database: %s", env_config.pg_database)
        yield _env_db(env_config)
    except RuntimeError as e:
        skip(str(e))


def _env_db(env_config):
    """Helper function to get the environment database without the fixture wrapper."""
    if env_config is None:
        raise RuntimeError("No environment configured")

    if env_config.pg_database is None:
        raise RuntimeError("No database configured for this environment")

    log.info("Connecting to database: %s", env_config.pg_database)
    db = Database(env_config.pg_database)

    # Change the user on the connection to a read-only user
    # TODO: verify read-only
    db.run_sql("SET ROLE web_anon;")
    return db


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

    from macrostrat.core.config import settings

    # If we have settings.databases.test defined, do the testing with a local database
    if settings.databases.get("test") and not request.config.getoption("--skip-env"):
        log.info("Using local database for testing")

        uri = settings.databases["test"]
        uri = make_url(uri)
        # https://github.com/psycopg/psycopg2/issues/916
        # We should probably integrate this into macrostrat.database module
        # https://github.com/UW-Macrostrat/python-libraries/issues/49
        uri = uri.set(drivername="postgresql+psycopg")
        log.info("Database URL: %s", uri)

        # Kludge to make sure we drop the database before creating it.
        # This solves a subtle
        with temporary_database(uri, ensure_empty=True, drop=False) as engine:
            assert engine.url.drivername == "postgresql+psycopg"
            log.info("Created temporary database: %s", engine.url)
            yield Database(engine)
        return

    with test_database_cluster(username="macrostrat_admin", optimize=optimize) as db:
        yield db


@fixture(scope="session")
def schema_harness(request, empty_db: Database):
    """Progressive, chunk-based schema builder shared across the session.

    The ``optimize`` transform (skipping indexes/grants/ownership) is applied by
    default for a faster build; disable with ``--no-optimize-database``.
    """
    from macrostrat.core.config import settings
    from macrostrat.schema_management.test_harness import DatabaseTestHarness

    optimize = request.config.getoption("--optimize-database")
    return DatabaseTestHarness(empty_db, env=settings.env, optimize=optimize)


from macrostrat.core.defs_provider import (
    MacrostratAPIConfig,
    MacrostratAPIDataProvider,
    MacrostratDatabaseDataProvider,
    MacrostratDataProvider,
    MacrostratMetadataPopulator,
)


@fixture(scope="session")
def data_provider(request):
    from macrostrat.core import get_database
    from macrostrat.core.config import settings

    source_db = None
    log.info("Attempting to connect to database %s", settings.pg_database)
    if not request.config.getoption("--skip-env"):
        try:
            source_db = get_database()
        except RuntimeError as e:
            log.warning("Could not connect to environment database: %s", e)
            log.warning("Defs will not be loaded from the API configuration")

    base_url = settings.base_url
    cfg = MacrostratAPIConfig(base_url=base_url + "/api/v2")
    data_provider = MacrostratAPIDataProvider(cfg)
    if source_db is not None:
        data_provider = MacrostratDatabaseDataProvider(source_db)
        log.info(
            "Set up Macrostrat data provider from database: %s", source_db.engine.url
        )
    else:
        log.info("Set up Macrostrat data provider using API: %s", cfg.base_url)
    yield data_provider


@fixture(scope="session")
def test_db_macrostrat_schema_only(
    schema_harness, data_provider: MacrostratDataProvider
):
    """A minimal database: the ``macrostrat`` subsystem and its dependencies."""
    db = schema_harness.load_schema(target="macrostrat")

    loader = MacrostratMetadataPopulator(data_provider, db)
    loader.populate_all()
    db.session.close()
    db.engine.dispose()
    yield db


@fixture(scope="class")
def test_db(test_db_macrostrat_schema_only: Database):
    db = test_db_macrostrat_schema_only
    with db.transaction(rollback=True):
        yield db


@fixture(scope="session")
def test_db_base(schema_harness, test_db_macrostrat_schema_only: Database):
    """The full-schema database used for testing.

    Builds every remaining chunk (maps, storage, tiles, …) on top of the minimal
    macrostrat build, so tests relying on e.g. ``macrostrat.maps`` have it.
    """
    return schema_harness.load_schema()


@fixture(scope="class")
def test_db_full(test_db_base: Database):
    with test_db_base.transaction(rollback=True):
        yield test_db_base
