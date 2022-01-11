import pytest
from backend.app import app
from backend.app.depends import get_db
from backend.database import Database
from backend.database.fixtures import get_sql
from fastapi.testclient import TestClient

# for testing the api
## https://fastapi.tiangolo.com/tutorial/testing/

testing_db = "postgresql://postgres@localhost:5434/col_test"

def override_get_db():
    db = Database(testing_db)
    return db
    
# override db dependency connection
## https://fastapi.tiangolo.com/advanced/testing-database/
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def connection():
    db = Database(testing_db)
    return db.conn

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

@pytest.fixture
def client(connection):
    return TestClient(app)