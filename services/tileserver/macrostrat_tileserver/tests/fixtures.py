from asyncio import run
from os import getenv
from pathlib import Path

from macrostrat.database import Database
from macrostrat.database.transfer import pg_restore_from_file
from macrostrat.database.utils import temp_database
from pytest import fixture
from sqlalchemy import Engine


def restore_database(engine: Engine, dumpfile: Path):
    run(pg_restore_from_file(dumpfile, engine))


__here__ = Path(__file__).parent


@fixture(scope="session")
def db(pytestconfig):
    # Check if we are dropping the database after tests
    drop = not pytestconfig.getoption("--no-drop")

    testing_db = getenv("TEST_DATABASE_URL")
    with temp_database(testing_db, drop=drop, ensure_empty=True) as engine:
        database = Database(engine.url)

        database.run_sql("CREATE ROLE postgres WITH SUPERUSER")

        restore_database(
            database.engine, __here__ / "test-fixtures" / "tileserver-test.pg-dump"
        )

        yield database
