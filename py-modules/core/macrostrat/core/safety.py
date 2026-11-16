"""The single write-authorization gate.

Every mutating command passes through :func:`require_write_access`, which reads
the active environment's :class:`~macrostrat.core.environment.EnvironmentPolicy`
and applies the gate guarding the scope being written:

.. code-block:: python

    @db_app.command()
    @writes(AccessScope.Data)
    def restore(...):
        ...

Two properties do the real work, and both are about what an *agent* can do.

**Non-interactive refusal.** `typed` and `escalate` read from a terminal, and an
agent has no TTY. So no amount of rephrasing a command, reordering its
arguments or setting an environment variable satisfies them — and that holds for
subagents and for anything invoked through `macrostrat run`.

**`escalate` ties write capability to human presence rather than to a decision
the process makes about itself.** It requires the writer credential to be a
secret-manager *reference* and re-fetches it, uncached, for this invocation.
Resolution goes through the password manager's own approval prompt, which an
LLM cannot answer. An environment whose writer credential is a literal in a
config file **cannot** satisfy `escalate` at all: there is nothing to
re-authorize against, so the gate fails closed and says so.

.. note:: On the bypass variable

   The plan for this stage specified a ``MACROSTRAT_ALLOW_WRITES=<env>``
   escape hatch for `confirm` in non-interactive contexts. It is deliberately
   **not implemented**. An environment variable is ambient, inherited by every
   subprocess, and — most importantly — *sticky*: set once in a deployment's
   configuration it authorizes writes for every later invocation, which is
   exactly the failure of `active_env` that this whole area exists to fix, one
   layer down. A per-invocation ``--yes`` flag on the command gives the same
   convenience with none of that, and cannot be set once and forgotten.
"""

from enum import Enum
from functools import wraps
from typing import Optional

from macrostrat.app_frame.environments import (
    AccessScope,
    EnvironmentPolicy,
    WriteGate,
    access,
)
from macrostrat.app_frame.environments.access import (  # noqa: F401
    AccessRefused,
    Refusal,
    StaleEnvironment,
    is_interactive,
)
from macrostrat.utils import get_logger

from .utils import active_environment, renew_active_env

log = get_logger(__name__)

#: A write was not authorized. Raised instead of proceeding.
WriteRefused = AccessRefused

# This module's own name for the prompt, so one seam covers every gate here.
_prompt = access.prompt


class _ActiveState:
    """The remembered environment, as the library's checks read it."""

    @property
    def active(self):
        return active_environment()

    def renew(self, ttl):
        return renew_active_env(ttl)


def _interactive() -> bool:
    return is_interactive()


def _ask(message: str) -> str:
    return _prompt(message)


def _resolve_policy(settings) -> EnvironmentPolicy:
    if settings is None:
        from .config import settings as _settings

        settings = _settings
    policy = getattr(settings, "policy", None)
    if policy is None:
        raise WriteRefused(
            "No environment policy could be resolved",
            details="Refusing to write. Select an environment with --env.",
        )
    return policy


def require_environment(*, settings=None, action: Optional[str] = None) -> None:
    """Confirm a *lapsed* environment before it is used, or raise.

    Called from the CLI's top-level callback for every command that could touch
    an environment, and again from :func:`require_write_access` so a write is
    covered even outside the CLI. Idempotent within an invocation.
    """
    state = _ActiveState()
    active = state.active
    if active is None or not active.needs_approval:
        return None
    access.require_environment(
        state,
        _resolve_policy(settings),
        command_name="macrostrat",
        action=action,
        interactive=_interactive,
        ask=_ask,
    )


def require_read_access(*, settings=None, action: Optional[str] = None) -> None:
    """Confirm a *read* against the active environment, or raise.

    Most environments do not gate reads and this returns at once. A production
    environment can declare ``confirm = { read = "prompt" }`` so that even
    opening a connection is a deliberate act; ``reauthorize`` re-fetches the
    reader credential. Passing never escalates the connection.
    """
    return _require_access(
        AccessScope.Read,
        settings=settings,
        action=action or "read",
        escalate_connection=False,
        role=DatabaseRoleName.Reader,
    )


#: Environments whose read gate this process has passed, so a command that
#: resolves the reader credential twice is asked once.
_reads_confirmed: set[str] = set()


def confirm_read(settings) -> None:
    """Pass *settings*' read gate, once per process; a no-op where reads are ungated."""
    policy = getattr(settings, "policy", None)
    if policy is None or policy.gate_for(AccessScope.Read) == WriteGate.NoGate:
        return
    key = policy.name or ""
    if key in _reads_confirmed:
        return
    require_read_access(settings=settings)
    _reads_confirmed.add(key)


def resolve_database_url(settings, role=None, name: Optional[str] = None):
    """*name*'s URL for *role*, resolving its credential now; None if unconfigured.

    The single place a credential is resolved from configuration, so the read
    gate cannot be skipped by a command that builds its own connection.
    """
    from .connections import DEFAULT_DATABASE, DatabaseRole

    role = DatabaseRole(role or DatabaseRole.Reader)
    conn = settings.database_connection(name or DEFAULT_DATABASE)
    if conn is None:
        return None
    if role == DatabaseRole.Reader:
        confirm_read(settings)
    return conn.url(role)


def require_write_access(
    scope,
    *,
    settings=None,
    assume_yes: bool = False,
    action: Optional[str] = None,
    escalate_connection: bool = True,
) -> None:
    """Authorize a write of *scope* against the active environment, or raise.

    Returns None when the write may proceed. Raises :class:`WriteRefused`
    otherwise — never returns a boolean, so a caller cannot accidentally ignore
    the answer.

    On success this also **escalates the invocation's database connection to
    the writer credential**. That is the whole mechanism by which write
    capability is acquired rather than held by default: `get_database()`
    connects as `Reader` until a gate passes. Because the connection is cached
    once per invocation, this needs no change at any of the call sites that
    merely use the database.

    Pass ``escalate_connection=False`` for a write that is not to the default
    database — a storage-only operation, say — so that authorizing it does not
    silently acquire database write capability as a side effect.
    """
    return _require_access(
        scope,
        settings=settings,
        assume_yes=assume_yes,
        action=action,
        escalate_connection=escalate_connection,
        role=DatabaseRoleName.Writer,
    )


class DatabaseRoleName(str, Enum):
    """Which credential an ``reauthorize`` level re-fetches."""

    Reader = "reader"
    Writer = "writer"


def _require_access(
    scope,
    *,
    settings=None,
    assume_yes: bool = False,
    action: Optional[str] = None,
    escalate_connection: bool = True,
    role: "DatabaseRoleName" = None,
) -> None:
    scope = AccessScope(scope)
    if role is None:
        role = DatabaseRoleName.Writer
    policy = _resolve_policy(settings)
    env = policy.name or "<no environment>"
    if action is not None:
        what = action
    elif scope == AccessScope.Read:
        what = "read"
    else:
        what = f"{scope.value} write"

    require_environment(settings=settings, action=what)

    access.require_access(
        scope,
        policy,
        assume_yes=assume_yes,
        action=what,
        # What `reauthorize` adds to typing the name: a fresh credential fetch.
        reauthorize=lambda _scope: _require_fresh_credential(settings, env, role),
        interactive=_interactive,
        ask=_ask,
    )

    # Write capability is acquired here rather than held: the connection is a
    # reader's until a gate passes.
    if escalate_connection:
        from .database import use_writer_connection

        use_writer_connection()
    return None


def _require_fresh_writer_credential(settings, env: str) -> None:
    """Re-fetch the writer credential. Kept for callers of the old name."""
    return _require_fresh_credential(settings, env, DatabaseRoleName.Writer)


def _require_fresh_credential(settings, env: str, role: "DatabaseRoleName") -> None:
    """Re-fetch the credential for *role*, uncached, for this invocation.

    This is what makes `escalate` different in kind from `typed` rather than
    merely stricter: resolution goes through the secret manager's own approval
    prompt. A cached value, an ambient `PGPASSWORD`, or a literal password in a
    config file all fail here, because none of them can be re-authorized.
    """
    from macrostrat.app_frame.secrets import Secret

    from .connections import DatabaseRole

    if settings is None:
        from .config import settings as _settings

        settings = _settings

    conn = settings.database_connection()
    if conn is None:
        raise WriteRefused(
            f"Cannot escalate in {env}: no database is configured",
            details="An escalate gate needs a writer credential to re-authorize.",
        )

    db_role = DatabaseRole(role.value)
    key = "write_password" if db_role == DatabaseRole.Writer else "read_password"
    try:
        credential = conn.credential_for(db_role)
    except Exception as err:
        raise WriteRefused(
            f"Cannot reauthorize in {env}: no {role.value} credential",
            details=str(err),
        ) from None

    if not isinstance(credential, Secret):
        raise WriteRefused(
            f"Cannot reauthorize in {env}: the {role.value} credential is a literal",
            details=(
                "The reauthorize level re-fetches the credential so the secret "
                "manager can require human approval. A password stored "
                "directly in macrostrat.toml cannot be re-authorized, so this "
                f"level fails closed. Move it to a reference ({key} = "
                '"op://...") or lower the level for this environment.'
            ),
        )

    # Drop any cached value so this fetch genuinely reaches the backend.
    credential.forget()
    credential.get()
    log.info(
        "%s credential for %s re-authorized for this invocation.",
        role.value.capitalize(),
        env,
    )


def writes(scope, *, action: Optional[str] = None):
    """Gate a command on *scope*, reading `--yes` from its own arguments.

    A command that wants a non-interactive path for a `confirm` gate declares
    ``yes: bool = Option(False, "--yes", "-y")``; the wrapper picks it up. There
    is no such path for `typed` or `escalate`.
    """

    def decorate(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            require_write_access(
                scope,
                assume_yes=bool(kwargs.get("yes", False)),
                action=action or fn.__name__.replace("_", " "),
            )
            return fn(*args, **kwargs)

        return wrapper

    return decorate
