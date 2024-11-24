from asyncio import run
from os import environ, getenv
from pathlib import Path

from fastapi.testclient import TestClient
from macrostrat.database import Database

from macrostrat.database.transfer import pg_restore_from_file
from macrostrat.database.utils import temp_database

# We could probably move this to a better location
from macrostrat.dinosaur.upgrade_cluster.utils import database_cluster
from pytest import fixture
from sqlalchemy import Engine
from docker.client import DockerClient


def restore_database(engine: Engine, dumpfile: Path):
    run(pg_restore_from_file(dumpfile, engine))


__here__ = Path(__file__).parent


@fixture(scope="session")
def test_database_url():
    # Get the database URL from the environment
    url = getenv("TEST_DATABASE_URL", None)
    if url is not None:
        return url

    # If we haven't provided a database URL , try to run a temporary database in Docker
    image = getenv("TEST_POSTGRES_IMAGE", "imresamu/postgis:15-3.4")
    client = DockerClient.from_env()
    port = 54280
    with database_cluster(client, image, port=port) as cluster:
        url = f"postgresql://postgres@localhost:{port}/tileserver_test_database"
        environ["TEST_DATABASE_URL"] = url
        yield url


@fixture(scope="session")
def db(pytestconfig, test_database_url):
    # Check if we are dropping the database after tests
    drop = not pytestconfig.getoption("--no-drop")

    print(f"Drop: {drop}")

    with temp_database(test_database_url, drop=drop, ensure_empty=True) as engine:
        database = Database(engine.url)

        database.run_sql("CREATE ROLE postgres WITH SUPERUSER")

        restore_database(
            database.engine, __here__ / "test-fixtures" / "tileserver-test.pg-dump"
        )

        yield database


@fixture(scope="session")
def app(db):
    environ["DATABASE_URL"] = getenv("TEST_DATABASE_URL")
    from macrostrat_tileserver.main import app

    yield app


@fixture(scope="session")
def client(app):
    with TestClient(app) as _client:
        yield _client
