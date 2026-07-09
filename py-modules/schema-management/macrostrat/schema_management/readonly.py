"""Enforced read-only access to a live database.

``SET ROLE web_anon`` is only *advisory* — a caller can ``RESET ROLE`` back to
the privileged connection role and write. To make read-only actually enforced we
connect as a role that has **no** write privileges in the first place: a superuser
mints an ephemeral ``LOGIN`` role that inherits ``pg_read_all_data`` (read
everything, write nothing) plus any roles we want to impersonate, hands back a
connection URL for it, and drops it afterward. Because that authenticated identity
can't write, no ``RESET ROLE`` can escalate.

Use :func:`readonly_login` to obtain the connection, :func:`assert_read_only` to
fail closed before trusting it, and :func:`as_role` to run reads as a specific
role (for grant / RLS testing).
"""

import secrets
from contextlib import contextmanager

from psycopg.sql import SQL, Identifier, Literal
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from macrostrat.database import Database
from macrostrat.utils import get_logger

log = get_logger(__name__)

# The built-in "read everything, write nothing" role (PostgreSQL 14+).
_READ_ALL = "pg_read_all_data"

# SQLSTATEs that mean a write was refused: insufficient_privilege /
# read_only_sql_transaction.
_WRITE_BLOCKED = {"42501", "25006"}


@contextmanager
def readonly_login(admin_input, *, impersonate=("web_anon",)):
    """Mint an ephemeral read-only login role; yield a connection URL for it.

    ``admin_input`` must be a superuser connection (URL/engine/Database) — it
    creates a throwaway ``LOGIN`` role that inherits ``pg_read_all_data`` plus the
    ``impersonate`` roles that actually exist (so tests can ``SET ROLE`` to them),
    yields a URL authenticated as that role, and drops it on exit.
    """
    admin = Database(admin_input)
    role = "macrostrat_ro_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)

    present = set(admin.run_query("SELECT rolname FROM pg_roles").scalars().all())
    member_of = [_READ_ALL] + [r for r in impersonate if r in present]

    created = False
    try:
        admin.run_sql(
            "CREATE ROLE {role} LOGIN PASSWORD {password} IN ROLE {members}",
            dict(
                role=Identifier(role),
                password=Literal(password),
                members=SQL(", ").join(Identifier(r) for r in member_of),
            ),
            raise_errors=True,
        )
        created = True
        log.info("Created ephemeral read-only role %s (member of %s)", role, member_of)
        yield admin.engine.url.set(username=role, password=password)
    finally:
        if created:
            admin.run_sql(
                "DROP ROLE IF EXISTS {role}",
                dict(role=Identifier(role)),
                raise_errors=True,
            )
        admin.engine.dispose()


def assert_read_only(db: Database) -> None:
    """Fail closed: prove the *authenticated* role cannot write.

    Drops any ``SET ROLE`` mask (``RESET ROLE``) then attempts a write inside a
    rolled-back transaction, so the probe never persists. Raises ``RuntimeError``
    if the write is accepted.
    """
    with db.engine.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(text("RESET ROLE"))
            conn.execute(text("CREATE TABLE _ro_probe (x int)"))
        except DBAPIError as err:
            if getattr(err.orig, "sqlstate", None) in _WRITE_BLOCKED:
                return  # good — the write was refused
            raise
        else:
            raise RuntimeError(
                "Database accepted a write on a connection that must be read-only; "
                "refusing to proceed."
            )
        finally:
            trans.rollback()


@contextmanager
def as_role(db: Database, role: str):
    """Run statements as ``role`` (``SET ROLE``), restoring the session after.

    For read-only grant / RLS testing: the impersonated role must be in the login
    role's membership closure (see ``impersonate`` in :func:`readonly_login`).
    """
    db.run_sql("SET ROLE {role}", dict(role=Identifier(role)), raise_errors=True)
    try:
        yield db
    finally:
        db.run_sql("RESET ROLE", raise_errors=True)
