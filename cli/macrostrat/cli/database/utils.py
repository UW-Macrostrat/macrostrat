from ._legacy import get_db
from sqlalchemy.engine import create_engine
from sqlalchemy.engine.url import URL, make_url
from macrostrat.core.config import settings
from sqlalchemy.engine import Engine
from macrostrat.database.utils import run_sql
from psycopg2.sql import Identifier
from contextlib import contextmanager
from uuid import uuid4


def engine_for_db_name(name: str | None):
    engine = get_db().engine
    if name is None:
        return engine
    url = engine.url.set(database=name)
    return create_engine(url)


def docker_internal_url(url: URL | str) -> URL:
    url = make_url(url)
    if url.host == "localhost":
        docker_localhost = getattr(settings, "docker_localhost", "localhost")
        url = url.set(host=docker_localhost)
    return url


@contextmanager
def pg_temp_engine(
    pg_engine: Engine, username: str, password: str = None, schemas: list[str] = None
):
    """Create a temporary login user for a PostgreSQL database with a limited set of permissions."""
    if password is None:
        password = str(uuid4().hex)

    run_sql(
        "CREATE USER {username} WITH PASSWORD {password}",
        dict(username=Identifier(username), password=password),
    )

    # Create a new database engine that uses the new user
    url = pg_engine.url.set(username=username, password=password)

    temp_engine = create_engine(url)

    if schemas is not None:
        for schema in schemas:
            run_sql(
                "CREATE SCHEMA IF NOT EXISTS {schema}",
                dict(schema=Identifier(schema)),
                engine=temp_engine,
            )

    yield temp_engine

    # Clean up
    run_sql("DROP USER {username}", dict(username=Identifier(username)))
