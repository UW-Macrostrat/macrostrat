import pytest
from .fixtures import get_sql, Database


@pytest.fixture(scope="session")
def db_():
    db = Database()
    return db

@pytest.fixture(scope="session")
def setup(db_):
    schema = get_sql("schema_dump.sql")
    data_inserts = get_sql("test_inserts.sql")
    with db_.conn.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS macrostrat_api CASCADE;")
        cur.execute("DROP SCHEMA IF EXISTS macrostrat CASCADE;")
        cur.execute(schema)
        cur.execute(data_inserts)

@pytest.fixture()
def db(setup, db_):
    return db_