"""Apply a schema-diff plan as the application owner where privileges allow.

A plan from ``results.dbdiff`` is a flat statement list with no chunk structure, so
it can't carry a per-chunk owner the way ``build_schema`` does — but it still
mostly creates ordinary application objects, which should be born ``macrostrat``-
owned rather than owned by whatever role happens to be connected (locally that is
``macrostrat_admin``, itself one of the roles ``ownership-unification`` sweeps).

So the plan runs under ``SET ROLE macrostrat``, and the statements that genuinely
need more — creating an extension, touching the shared ``public``/``topology``
schemas, re-owning an object ``macrostrat`` doesn't own — are re-run as the
connector through an ``on_error`` recovery hook. Privilege is what separates the
two cases and Postgres already reports it, so this reacts to `42501` rather than
trying to classify statements up front.
"""

from contextlib import contextmanager

from macrostrat.core.database import pin_role
from macrostrat.database import Database
from macrostrat.utils import get_logger

from .composer import APP_OWNER, set_applying_role

log = get_logger(__name__)

# SQLSTATE 42501 (insufficient_privilege) — the application role can't do this, so
# the statement belongs to the connector.
_INSUFFICIENT_PRIVILEGE = "42501"


def _is_privilege_error(err: Exception) -> bool:
    """Whether ``err`` is Postgres refusing the statement to the current role.

    Read from the driver exception SQLAlchemy wraps (``.orig``); psycopg 3 spells
    the code ``sqlstate`` and psycopg 2 ``pgcode``, and both drivers are installed.
    """
    orig = getattr(err, "orig", err)
    code = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    return code == _INSUFFICIENT_PRIVILEGE


@contextmanager
def applied_as_app_owner(db: Database):
    """Run a block's DDL as ``macrostrat``, yielding an ``on_error`` hook to pass on.

    The hook re-runs a statement the application role was refused as the
    connector, then restores the role for the rest of the plan. It runs the
    statement itself rather than returning ``RESET ROLE`` / statement / ``SET
    ROLE`` directives: each directive commits on its own, and the role is pinned
    to every connection the engine hands out (``set_applying_role``), so a reset
    issued as a separate statement would not carry over to the next one.

    Yields ``None`` -- leaving the session as the connector, i.e. the previous
    behaviour -- when the connector isn't a member of ``macrostrat`` and so can't
    take the role at all.
    """
    try:
        set_applying_role(db, APP_OWNER)
    except Exception as err:  # noqa: BLE001 — degrade to the connector, don't fail
        log.warning(
            "Could not apply as %s (%s); running as the connector instead.",
            APP_OWNER,
            err,
        )
        yield None
        return

    def escalate(ctx, err, connectable):
        if not _is_privilege_error(err):
            return None  # not ours to handle — fall through to normal handling
        log.info("Statement needs the connector's privileges: %s", ctx.sql_text[:100])
        set_applying_role(db, None)
        try:
            db.run_sql(ctx.query, ctx.params, raise_errors=True)
        except Exception as retry_err:  # noqa: BLE001 — reported as the original
            log.error("Statement failed as the connector too: %s", retry_err)
            return None
        finally:
            set_applying_role(db, APP_OWNER)
        return []  # handled: nothing further to run

    try:
        yield escalate
    finally:
        pin_role(db.engine, None)
        db.run_sql("RESET ROLE", raise_errors=False)
