import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

testing_db = "postgresql://postgres@localhost:5434/col_test"

@pytest.fixture(scope="session")
def connection():
    engine = create_engine(testing_db)
    return engine.connect()

@pytest.fixture
def db(connection):
    transaction = connection.begin()
    yield scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=connection)
    )
    transaction.rollback()