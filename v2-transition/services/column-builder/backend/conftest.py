import pytest
from psycopg import connect, rows

testing_db = "postgresql://postgres@localhost:5434/col_test"

@pytest.fixture(scope="session")
def connection():
    conn = connect(testing_db, row_factory=rows.dict_row)
    return conn

@pytest.fixture
def db(connection):
    with connection.cursor() as cur:
        yield cur
    connection.rollback()    