from contextlib import contextmanager
from typing import Optional
from uuid import uuid4

from psycopg2.sql import Identifier
from rich import print
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.engine.url import URL, make_url

from macrostrat.core.config import settings
from macrostrat.database import Database
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


class Permission(Enum):
    Select = "SELECT"
    Insert = "INSERT"
    Update = "UPDATE"
    Delete = "DELETE"
    Truncate = "TRUNCATE"
    References = "REFERENCES"
    Trigger = "TRIGGER"
    Create = "CREATE"
    Connect = "CONNECT"
    Temporary = "TEMPORARY"
    Usage = "USAGE"
    Execute = "EXECUTE"
    All = "ALL"


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


def get_table_permissions(db, schema, table, user) -> set[Permission]:
    """Check if a user has the required permissions on a table"""
    db = get_db()
    perms = db.run_query(
        "SELECT privilege_type FROM information_schema.table_privileges WHERE table_schema = :schema AND table_name = :table AND grantee = :user",
        dict(schema=schema, table=table, user=user),
    )
    return {Permission(p) for p in perms.scalars()}


def grant_permissions(
    schema, user, *_permissions, owner=False, tables: list[str] = None
):
    """Higher-order function to grant permissions on a schema to a user"""

    def setup_permissions(db):
        """Set permissions on tables in the knowledge graph subsystem"""
        permissions = [p for p in _permissions]
        if owner:
            permissions = ["ALL"]

        if len(permissions) == 0:
            permissions = ["SELECT"]

        _perms = ", ".join(permissions)
        print(
            f"Grant {_perms} on  schema [cyan bold]{schema}[/] to [cyan bold]{user}[/]"
        )

        if tables is None:
            tables = db.run_query(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = :schema",
                dict(schema=schema),
            )
        stmts = [
            (
                "GRANT USAGE ON SCHEMA {schema} TO {user}",
                dict(schema=Identifier(schema), user=Identifier(user)),
            )
        ]

        has_create = "CREATE" in permissions or "ALL" in permissions
        table_perms = [p for p in permissions if p != "CREATE"]

        # Give permissions to create objects in the schema
        if owner or has_create:
            stmts.append(
                (
                    "GRANT CREATE ON SCHEMA {schema} TO {user}",
                    dict(schema=Identifier(schema), user=Identifier(user)),
                )
            )

        for table in tables.scalars():
            params = dict(table=Identifier(schema, table), user=Identifier(user))
            existing_perms = get_table_permissions(db, schema, table, user)

            if owner:
                stmts.append(
                    (
                        "ALTER TABLE {table} OWNER TO {user}",
                        params,
                    )
                )
            for perm in table_perms:
                if Permission(perm) in existing_perms:
                    continue
                stmts.append(
                    (
                        "GRANT " + perm + " ON {table} TO {user}",
                        params,
                    )
                )

        # Functions
        functions = db.run_query(
            "SELECT routine_name FROM information_schema.routines WHERE routine_schema = :schema",
            dict(schema=schema),
        )
        # Grant usage of functions
        fn_perms = [p for p in permissions if p in ("EXECUTE", "ALL")]
        for function in functions.scalars():
            params = dict(function=Identifier(schema, function), user=Identifier(user))
            for perm in fn_perms:
                stmts.append(
                    (
                        "GRANT " + perm + " ON FUNCTION {function} TO {user}",
                        params,
                    )
                )

            # Grant ownership of functions
            if owner:
                params = dict(
                    function=Identifier(schema, function), user=Identifier(user)
                )
                stmts.append(
                    (
                        "ALTER FUNCTION {function} OWNER TO {user}",
                        params,
                    )
                )

        # Views
        views = db.run_query(
            "SELECT table_name FROM information_schema.views WHERE table_schema = :schema",
            dict(schema=schema),
        )
        # Grant usage of views
        view_perms = [p for p in permissions if p in ("SELECT", "ALL")]

        for view in views.scalars():
            params = dict(view=Identifier(schema, view), user=Identifier(user))
            for perm in view_perms:
                stmts.append(
                    (
                        "GRANT " + perm + " ON {view} TO {user}",
                        params,
                    )
                )

        for stmt in stmts:
            db.run_sql(*stmt)
            db.session.commit()

    return setup_permissions


def grant_schema_ownership(schema, owner):
    """Higher-order function to grant ownership of a schema to a user"""
    return grant_permissions(schema, owner, owner=True)


def grant_schema_usage(
    db: Database,
    schema: str,
    role: str,
    *,
    tables: bool = True,
    sequences: bool = False,
):
    """
    Some basic permissions need to be set in order for the PostgREST service to
    be able to access the schema.
    :return:
    """
    params = dict(schema=Identifier(schema), role=Identifier(role))

    db.run_sql("GRANT USAGE ON SCHEMA {schema} TO {role}", params)

    if tables:
        db.run_sql(
            """
        GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {role};
        ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT SELECT ON TABLES TO {role};
        """,
            params,
        )

    if sequences:
        db.run_sql(
            """
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {schema} TO {role};
        ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT USAGE, SELECT ON SEQUENCES TO {role};
        """,
            params,
        )


def setup_postgrest_access(
    schema: str,
    *,
    read_user: str = "web_anon",
    write_user: Optional[str] = "web_user",
):
    """Run basic grant statements to allow PostgREST to access the schema"""

    def run_updates(db):
        grant_schema_usage(db, schema, read_user)
        if write_user is not None:
            grant_schema_usage(db, schema, write_user, tables=False, sequences=True)

    return run_updates
