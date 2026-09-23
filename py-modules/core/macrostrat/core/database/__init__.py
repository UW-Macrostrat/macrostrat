from contextlib import contextmanager
from contextvars import ContextVar
from os import environ
from weakref import WeakKeyDictionary

from click.exceptions import ClickException
from sqlalchemy import create_engine, event

from macrostrat.database import Database
from macrostrat.utils import get_logger

from ..config import PG_DATABASE, settings
from ..connections import DEFAULT_DATABASE, DatabaseRole, connection_for
from ..environment import WriteGate, WriteScope
from ..exc import MacrostratError

log = get_logger(__name__)

db_ctx: ContextVar[Database | None] = ContextVar("db_ctx", default=None)

#: The privilege this invocation connects with. `Reader` until something asks
#: to write, which in practice means until a write gate passes.
#:
#: Per *invocation*, not per call site. `get_database()` caches one `Database`
#: in `db_ctx`, so there is exactly one role decision per process — which is
#: why narrowing the default does not require touching any of the ~155
#: `get_database()` call sites.
db_role_ctx: ContextVar[DatabaseRole] = ContextVar(
    "db_role_ctx", default=DatabaseRole.Reader
)


def _default_database_url():
    """The URL `get_database()` connects with, for the current role.

    `PG_DATABASE` is the literal from config and stays the source of truth
    whenever there is one — and note it is **role-independent**, so on a config
    holding a literal connection URL the role has no effect at all. It is None
    only when the environment names its credentials in a secret manager.
    """
    if PG_DATABASE is not None:
        return PG_DATABASE
    return settings.database_url(db_role_ctx.get())


def current_database_role() -> DatabaseRole:
    """The privilege this invocation is currently connected with."""
    return db_role_ctx.get()


def use_writer_connection() -> None:
    """Escalate this invocation to the writer credential.

    Called when a write has been authorized — from `require_write_access`, so
    that passing a gate is what grants write capability rather than every
    command holding it by default.

    Idempotent. If a reader connection is already open — a command that read
    something before asking to write — it is closed and dropped so the next
    `get_database()` reconnects with the writer credential.
    """
    if db_role_ctx.get() == DatabaseRole.Writer:
        return
    db_role_ctx.set(DatabaseRole.Writer)

    existing = db_ctx.get()
    if existing is None:
        return
    # Best-effort teardown: this connection is being replaced, and a failure
    # to close it cleanly must not stop the authorized write from proceeding.
    try:
        existing.session.close()
    except Exception:  # pragma: no cover - depends on session state
        log.debug("Could not close the reader session before escalating")
    try:
        existing.engine.dispose()
    except Exception:  # pragma: no cover
        log.debug("Could not dispose the reader engine before escalating")
    db_ctx.set(None)


class NoDatabaseConfigured(MacrostratError, ClickException):
    """No connection URL could be composed for the active environment.

    Raised instead of handing `None` to the engine, which failed several
    frames down with `Invalid input type: None` — the error people met after a
    remembered environment lapsed, and the reason it read as a crash rather
    than as "you have no environment".
    """

    exit_code = 1

    def __init__(self):
        env = environ.get("MACROSTRAT_ENV")
        if env:
            message = f"No database is configured for environment {env}"
            details = (
                f"Add pg_database or a [{env}.database] table to its section in "
                "macrostrat.toml."
            )
        else:
            message = "No environment is active, so there is no database to use"
            details = (
                "Run `macrostrat env <name>` to activate one, or pass --env <name> "
                "for a single command. `macrostrat config environments` lists them."
            )
        MacrostratError.__init__(self, message, details)

    def format_message(self) -> str:
        return f"{self.message}\n{self.details}"


def _confirm_read_if_gated() -> None:
    """Ask before the first read connection, where the environment says to.

    Almost every environment leaves reads ungated and this costs a dictionary
    lookup. A production environment declaring ``confirm = { read = … }``
    makes even opening a connection deliberate — and, since the prompt needs a
    terminal, unavailable to an agent. Writers have already passed a write
    gate, so only the reader role is asked.
    """
    if db_role_ctx.get() != DatabaseRole.Reader:
        return
    policy = getattr(settings, "policy", None)
    if policy is None or policy.gate_for(WriteScope.Read) == WriteGate.NoGate:
        return
    from ..safety import require_read_access

    require_read_access(settings=settings)


#: The main database's name in the connection registry; `[<env>.databases]`
#: holds everything else. Kept as an alias so callers can say what they mean.
MAIN_DATABASE = DEFAULT_DATABASE


def _settings_for_env(env: str | None):
    """A settings object for a named environment, under either config loader.

    The point of naming an environment here is to reach a *known* deployment
    without the CLI having selected it, so this deliberately does not touch the
    active-environment pointer.
    """
    if env is None or env == getattr(settings, "env", None):
        return settings

    from ..config import IS_V2

    if IS_V2:
        from ..config_loader import load_settings_v2

        return load_settings_v2(settings.config_file, env)
    # Dynaconf's per-environment view. Absent on the v2 settings object, which
    # is why this goes through the loader above instead.
    return settings.from_env(env)


def database_url_for(name: str = MAIN_DATABASE, env: str | None = None) -> str:
    """Look up a database URL by name, optionally in a named environment.

    Independent of the process-global active environment, so a caller can target a
    known deployment without the CLI having selected it first — which is what makes
    a pipeline runnable against `test` without changing anything persistent.

    Composed through the connection registry rather than read from a config key,
    so an environment whose credentials live in a secret manager resolves here
    too, and a `[<env>.databases]` entry written as a bare name inherits its
    server. The URL is for handing to another process, so it carries the write
    login and none of this process's `application_name` attribution.
    """
    from ..config import exported_database_url

    cfg = _settings_for_env(env)
    conn = connection_for(cfg, name)
    if conn is None:
        where = f"environment {env!r}" if env else "the active environment"
        raise KeyError(f"No database {name!r} configured for {where}")
    return exported_database_url(conn, DatabaseRole.Writer)


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
        url = _default_database_url()
        if url is None:
            raise NoDatabaseConfigured()
        _confirm_read_if_gated()
        db = Database(url)
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
