import os

from pytest import fixture


@fixture(scope="session", autouse=True)
def setup_session():
    # Set the PG_DATABASE environment variable to a shim value, since
    # tests should run without a database connection string defined.
    # The strategy for dealing with this will have to be improved in the future.
    os.environ["PG_DATABASE"] = (
        "postgresql://nonexistent-host.local:54328/nonexistent-database"
    )
    yield
