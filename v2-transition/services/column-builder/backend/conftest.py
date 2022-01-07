import pytest
from psycopg import connect, rows
from backend.database.fixtures import get_sql

testing_db = "postgresql://postgres@localhost:5434/col_test"

@pytest.fixture(scope="session")
def connection():
    conn = connect(testing_db, autocommit=True,row_factory=rows.dict_row)

    return conn

@pytest.fixture(scope="session")
def setup(connection):
    schema = get_sql("schema_dump.sql")
    data_inserts = get_sql("test_inserts.sql")
    with connection.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS macrostrat CASCADE;")
        cur.execute(schema)
        cur.execute(data_inserts)
 
@pytest.fixture
def db(setup, connection):
    with connection.cursor() as cur:
        yield cur
    connection.rollback()    