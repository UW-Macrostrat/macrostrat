from contextlib import contextmanager
from typing import Optional
from uuid import uuid4

from psycopg2.sql import Identifier
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.engine.url import URL, make_url

from macrostrat.core.config import settings
from macrostrat.database.utils import run_query, run_sql

from ._legacy import get_db


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
def pg_temp_user(
    pg_engine: Engine, username: str, *, password: str = None, overwrite: bool = False
):
    """Create a temporary login user for a PostgreSQL database with a limited set of permissions."""
    # Check whether the user already exists
    exists = has_user(pg_engine, username)
    if exists:
        if overwrite:
            drop_user(
                pg_engine,
                username,
                owned_by=OwnedByPolicy.Reassign,
            )
        else:
            raise ValueError(f"User {username} already exists")

    if password is None:
        password = str(uuid4().hex)

    run_sql(
        pg_engine,
        "CREATE USER {username} WITH PASSWORD :password",
        dict(username=Identifier(username), password=password),
    )

    # Create a new database engine that uses the new user
    url = pg_engine.url.set(username=username).set(password=password)

    try:
        temp_engine = create_engine(url)
        yield temp_engine
        temp_engine.dispose()
    finally:
        # Clean up
        drop_user(
            pg_engine,
            username,
            owned_by=OwnedByPolicy.Reassign,
        )


from enum import Enum
from warnings import warn


class OwnedByPolicy(Enum):
    Reassign = "reassign"
    Drop = "drop"
    Restrict = "restrict"


def drop_user(
    engine: Engine,
    username: str,
    *,
    owned_by: Optional[OwnedByPolicy] = OwnedByPolicy.Restrict,
    allow_privilege_escalation: bool = True,
):
    params = dict(username=Identifier(username))
    if owned_by == OwnedByPolicy.Reassign:
        # Check for privilege escalation
        reassign_privileges(
            engine, username, allow_privilege_escalation=allow_privilege_escalation
        )
    if owned_by in (OwnedByPolicy.Drop, OwnedByPolicy.Reassign):
        # Drop all objects owned by the user (this actually drops permissions).
        # It is hard to drop all objects owned by a user without using this sort
        # of intense approach.
        run_sql(engine, "DROP OWNED BY {username}", params)

    run_sql(
        engine,
        "DROP USER {username}",
        params,
    )


def has_user(engine: Engine, username: str) -> bool:
    """Check if a database role exists in a PostgreSQL database."""
    return (
        run_query(
            engine,
            "SELECT 1 FROM pg_roles WHERE rolname = :username",
            dict(username=username),
        ).scalar()
        is not None
    )


def is_superuser(engine: Engine, username: str) -> bool:
    return run_query(
        engine,
        "select usesuper from pg_user where usename = :username",
        dict(username=username),
    ).scalar()


def reassign_privileges(
    engine: Engine,
    from_user: str,
    to_user: str = None,
    *,
    allow_privilege_escalation: bool = True,
):
    """Reassign all objects owned by one user to another user, reporting
    privilege escalation that may not be desired."""

    if to_user is None:
        to_user = engine.url.username
    # Check for privilege escalation
    if not is_superuser(engine, from_user) and is_superuser(
        engine, engine.url.username
    ):
        warning = "Privilege escalation to superuser may not be desired."
        if not allow_privilege_escalation:
            raise ValueError(warning)
        warn(warning)

    run_sql(
        engine,
        "REASSIGN OWNED BY {from_user} TO {to_user}",
        dict(from_user=Identifier(from_user), to_user=Identifier(to_user)),
    )