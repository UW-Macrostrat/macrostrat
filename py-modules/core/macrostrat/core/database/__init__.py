from contextlib import contextmanager
from contextvars import ContextVar
from weakref import WeakKeyDictionary

from sqlalchemy import create_engine, event

from macrostrat.database import Database

from ..config import PG_DATABASE, settings

db_ctx: ContextVar[Database | None] = ContextVar("db_ctx", default=None)

# `pg_database` is the main database's key in the config; the named registry in
# `[<env>.databases]` holds everything else.
MAIN_DATABASE = "macrostrat"


def database_url_for(name: str = MAIN_DATABASE, env: str | None = None) -> str:
    """Look up a database URL by name, optionally in a named environment.

    Independent of the process-global active environment, so a caller can target a
    known deployment without the CLI having selected it first — which is what makes
    a pipeline runnable against `test` without changing anything persistent.
    """
    cfg = settings if env is None else settings.from_env(env)
    if name == MAIN_DATABASE:
        # Injected into `settings.databases` at import rather than written in the
        # TOML, so it is not in the registry when reached through `from_env`.
        url = cfg.get("pg_database")
    else:
        url = (cfg.get("databases") or {}).get(name)
    if url in (None, "None"):
        where = f"environment {env!r}" if env else "the active environment"
        raise KeyError(f"No database {name!r} configured for {where}")
    return str(url)


def database_for(name: str = MAIN_DATABASE, env: str | None = None) -> Database:
    """Resolve a named database from configuration. See `database_url_for`.

    Pass the result explicitly to library functions, or install it for code that
    still resolves its own with `get_database()`:

        with database_context(database_for(env="test")):
            ...
    """
    return Database(database_url_for(name, env))


def get_database():
    from macrostrat.database import Database

    db = db_ctx.get()
    if db is None:
        db = Database(PG_DATABASE)
        db_ctx.set(db)
    return db


def refresh_database():
    db = get_database()
    db.session.flush()
    db.session.close()
    db_ctx.set(None)
    return get_database()


def engine_for_db_name(name: str | None):
    engine = get_database().engine
    if name is None:
        return engine
    url = engine.url.set(database=name)
    return create_engine(url)


@contextmanager
def database_context(db: Database):
    """Set the active database for the duration of the context."""
    prev = db_ctx.get()
    db_ctx.set(db)
    yield db
    db_ctx.set(prev)


# Session-scoped audit context, per engine. Kept so a re-set replaces the previous
# listener rather than stacking another one on every call.
_audit_listeners: WeakKeyDictionary = WeakKeyDictionary()


def _pin_audit_context(engine, actor: str, batch: str | None):
    """Apply the audit context to every connection this engine hands out.

    Setting it on whichever connection we happen to hold is not enough: a job that
    runs long enough for the pool to hand it a different connection would silently
    start writing unattributed rows. Applying it on checkout makes the context a
    property of the job rather than of one connection.
    """
    previous = _audit_listeners.pop(engine, None)
    if previous is not None:
        event.remove(engine, "checkout", previous)

    def apply_context(dbapi_connection, connection_record, connection_proxy):
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.actor_id', %s, false)", (actor,))
            cursor.execute(
                "SELECT set_config('app.batch_id', %s, false)", (batch or "",)
            )

    event.listen(engine, "checkout", apply_context)
    _audit_listeners[engine] = apply_context


def set_audit_context(
    db: Database, actor: str, batch: str | None = None, *, local: bool = True
) -> bool:
    """Attribute this job's writes in the change-tracking trail.

    Writes captured by the audit triggers (``schema/_definitions/audit/``) carry
    whatever actor and batch the session declares. Machine writes should say so: it
    is what lets a reader tell curation from recomputation, and what makes a batch
    prunable afterwards (``record_history_batch_idx`` indexes ``batch_id``).

    ``local`` picks the scope, and getting it wrong loses attribution silently —
    rows land with a null actor rather than raising:

    - ``True`` (default): scoped to the current transaction. Correct when the writes
      share one, e.g. column ingestion inside ``db.transaction()``.
    - ``False``: scoped to the session, and re-applied on every connection checkout
      so it survives pooling. Needed for jobs that issue many statements without
      wrapping them, e.g. the rebuild scripts running through ``run_sql`` in
      autocommit. Pass an empty actor to clear it.

    Returns False (and does nothing) when the audit subsystem is not installed. The
    check happens here rather than inside the statement because the function is
    resolved at parse time, so a guard in SQL would still fail.
    """
    installed = db.run_query(
        "SELECT to_regprocedure('audit.set_context(text,text,boolean)') IS NOT NULL AS ok"
    ).scalar()
    if not installed:
        return False
    if not local:
        # An empty actor means "clear": drop the listener rather than pinning blanks
        # onto every future checkout.
        if actor:
            _pin_audit_context(db.engine, actor, batch)
        else:
            previous = _audit_listeners.pop(db.engine, None)
            if previous is not None:
                event.remove(db.engine, "checkout", previous)
    db.run_sql(
        "SELECT audit.set_context(:actor, :batch, :local)",
        dict(actor=actor, batch=batch, local=local),
        raise_errors=True,
    )
    return True
