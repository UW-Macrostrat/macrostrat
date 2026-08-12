from asyncio import run
from os import environ, getenv
from pathlib import Path

from fastapi.testclient import TestClient
from pytest import fixture
from sqlalchemy import Engine
from sqlalchemy.engine import make_url
from testcontainers.postgres import PostgresContainer

from macrostrat.database import Database
from macrostrat.database.transfer import pg_restore_from_file
from macrostrat.database.utils import temp_database


def restore_database(engine: Engine, dumpfile: Path):
    run(pg_restore_from_file(dumpfile, engine))


__here__ = Path(__file__).parent

# Name of the database the test schema is restored into.
TEST_DATABASE = "tileserver_test_database"


@fixture(scope="session")
def test_database_url():
    """A PostgreSQL server to build the test database on.

    Either one provided by the environment, or a throwaway PostGIS container.
    testcontainers is used directly rather than through
    `macrostrat.dinosaur.database_cluster`: all that's needed is a container with
    PostGIS in it, and depending on the migration library here would drag its
    local-path sources into this service's lock file (which then breaks the
    Docker build, since only the raster libraries are copied into the image).
    """
    url = getenv("TEST_DATABASE_URL", None)
    if url is not None:
        yield url
        return

    image = getenv("TEST_POSTGRES_IMAGE", "imresamu/postgis:15-3.4")
    container = PostgresContainer(image, username="postgres", dbname="postgres")
    container.with_env("POSTGRES_HOST_AUTH_METHOD", "trust")
    container.start()
    try:
        # The container picks its own host port. The driver is stripped from the
        # scheme because the app connects with asyncpg, which rejects
        # SQLAlchemy's `postgresql+psycopg` form; the schema is restored into its
        # own database on that server.
        url = str(
            make_url(container.get_connection_url()).set(
                drivername="postgresql", database=TEST_DATABASE
            )
        )
        environ["TEST_DATABASE_URL"] = url
        yield url
    finally:
        container.stop()


@fixture(scope="session")
def db(pytestconfig, test_database_url):
    # Check if we are dropping the database after tests
    drop = not pytestconfig.getoption("--no-drop")

    print(f"Drop: {drop}")

    with temp_database(test_database_url, drop=drop, ensure_empty=True) as engine:
        database = Database(engine.url)

        # The dump is owned by `postgres`; the container may already have that
        # role (it's the default superuser), so creating it has to be tolerant.
        database.run_sql(
            """
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
                CREATE ROLE postgres WITH SUPERUSER LOGIN;
              END IF;
            END $$;
            """
        )

        restore_database(
            database.engine, __here__ / "test-fixtures" / "tileserver-test.pg-dump"
        )
        database.run_fixtures(__here__ / "test-fixtures" / "setup.sql")
        # The dump predates database-side tile caching.
        database.run_fixtures(__here__ / "test-fixtures" / "tile-cache.sql")

        yield database


@fixture(scope="session")
def app(db):
    environ["DATABASE_URL"] = getenv("TEST_DATABASE_URL")
    from macrostrat.tileserver import app

    yield app


@fixture(scope="session")
def client(app):
    with TestClient(app) as _client:
        yield _client
