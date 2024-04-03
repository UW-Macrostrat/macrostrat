from macrostrat.database.utils import temp_database
from macrostrat.database import Database
from pytest import fixture
from os import getenv

testing_db = getenv("TEST_DATABASE_URL")

@fixture(scope="session")
def empty_db(pytestconfig):
    # Check if we are dropping the database after tests
    drop = not pytestconfig.getoption("--no-drop")

    with temp_database(testing_db, drop=drop, ensure_empty=True) as engine:
        database = Database(engine.url)
        database.set_active()
        yield database