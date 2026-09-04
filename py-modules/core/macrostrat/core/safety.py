"""The single write-authorization gate.

Every mutating command passes through :func:`require_write_access`, which reads
the active environment's :class:`~macrostrat.core.environment.EnvironmentPolicy`
and applies the gate guarding the scope being written:

.. code-block:: python

    @db_app.command()
    @writes(WriteScope.Data)
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

import sys
from functools import wraps
from typing import Optional

from click.exceptions import ClickException

from macrostrat.utils import ApplicationError, get_logger

from .environment import EnvironmentPolicy, WriteGate, WriteScope

log = get_logger(__name__)


class WriteRefused(ApplicationError, ClickException):
    """A write was not authorized. Raised instead of proceeding.

    Also a `ClickException` so that Click renders it as an error and exits 1,
    rather than letting it escape as a traceback. That matters more here than
    for an ordinary error: a refusal that *looks* like a crash invites someone
    to retry harder or assume the tool is broken, which is the opposite of
    what a guard rail should communicate.

    (The CLI's own `setup_exception_handling` wrapper, which would render every
    `ApplicationError` this way, is commented out in `cli/entrypoint.py` — so
    every `MacrostratError` currently surfaces as a traceback. Worth fixing
    separately; this class does not depend on it either way.)
    """

    def __init__(self, message: str, details: Optional[str] = None):
        ApplicationError.__init__(self, message, details)
        self.exit_code = 1

    def format_message(self) -> str:
        if self.details:
            return f"{self.message}\n{self.details}"
        return self.message


def is_interactive() -> bool:
    """Whether a human is plausibly present at a terminal.

    Requires both a readable TTY and a TTY to prompt on. Agents, CI jobs, cron
    and `subprocess` calls have neither.
    """
    try:
        return sys.stdin.isatty() and sys.stderr.isatty()
    except (AttributeError, ValueError):  # detached or closed streams
        return False


def _prompt(message: str) -> str:
    """Ask on stderr, read from stdin.

    stderr so a prompt never lands in a command's piped stdout.
    """
    print(message, end="", file=sys.stderr, flush=True)
    return sys.stdin.readline().strip()


def _resolve_policy(settings) -> EnvironmentPolicy:
    if settings is None:
        from .config import settings as _settings

        settings = _settings
    policy = getattr(settings, "policy", None)
    if policy is None:
        # No policy at all is not a reason to allow a write.
        raise WriteRefused(
            "No environment policy could be resolved",
            details="Refusing to write. Select an environment with --env.",
        )
    return policy


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
    scope = WriteScope(scope)
    policy = _resolve_policy(settings)
    gate = policy.gate_for(scope)
    env = policy.name or "<no environment>"
    what = action or f"{scope.value} write"

    inferred = ""
    if policy.inferred:
        inferred = (
            f" This environment declares no class, so it is treated as "
            f"{policy.env_class.value} ({policy.reason})."
        )

    def _authorized():
        """The single success path, so escalation cannot be forgotten."""
        if escalate_connection:
            from .database import use_writer_connection

            use_writer_connection()
        return None

    if gate == WriteGate.NoGate:
        log.debug("%s in %s is ungated (%s).", what, env, policy.env_class.value)
        return _authorized()

    if gate == WriteGate.Confirm:
        if assume_yes:
            log.warning(
                "Proceeding with %s in %s (%s) because --yes was passed.",
                what,
                env,
                policy.env_class.value,
            )
            return _authorized()
        if not is_interactive():
            raise WriteRefused(
                f"Refusing {what} in {env} ({policy.env_class.value})",
                details=(
                    "This gate needs confirmation and there is no terminal to "
                    f"ask on. Re-run it interactively, or pass --yes.{inferred}"
                ),
            )
        answer = _prompt(f"{what.capitalize()} in {env}. Proceed? [y/N] ")
        if answer.lower() not in ("y", "yes"):
            raise WriteRefused(f"{what.capitalize()} in {env} was declined")
        return _authorized()

    # `typed` and `escalate` are never satisfiable without a terminal, and
    # --yes deliberately does not help.
    if not is_interactive():
        raise WriteRefused(
            f"Refusing {what} in {env} ({policy.env_class.value})",
            details=(
                f"The {gate.value!r} gate guarding {scope.value} writes here "
                "requires an interactive terminal. There is no flag or "
                f"environment variable that satisfies it.{inferred}"
            ),
        )

    typed = _prompt(
        f"{what.capitalize()} in {env} ({policy.env_class.value}). "
        f"Type the environment name to proceed: "
    )
    if typed != env:
        raise WriteRefused(
            f"Refusing {what} in {env}",
            details=f"Expected {env!r}, got {typed!r}.",
        )

    if gate == WriteGate.Escalate:
        _require_fresh_writer_credential(settings, env)

    return _authorized()


def _require_fresh_writer_credential(settings, env: str) -> None:
    """Re-fetch the writer credential, uncached, for this invocation.

    This is what makes `escalate` different in kind from `typed` rather than
    merely stricter: resolution goes through the secret manager's own approval
    prompt. A cached value, an ambient `PGPASSWORD`, or a literal password in a
    config file all fail here, because none of them can be re-authorized.
    """
    from .connections import DatabaseRole
    from .secrets import Secret

    if settings is None:
        from .config import settings as _settings

        settings = _settings

    conn = settings.database_connection()
    if conn is None:
        raise WriteRefused(
            f"Cannot escalate in {env}: no database is configured",
            details="An escalate gate needs a writer credential to re-authorize.",
        )

    try:
        credential = conn.credential_for(DatabaseRole.Writer)
    except Exception as err:
        raise WriteRefused(
            f"Cannot escalate in {env}: no writer credential",
            details=str(err),
        ) from None

    if not isinstance(credential, Secret):
        raise WriteRefused(
            f"Cannot escalate in {env}: the writer credential is a literal",
            details=(
                "An escalate gate re-fetches the credential so the secret "
                "manager can require human approval. A password stored "
                "directly in macrostrat.toml cannot be re-authorized, so this "
                "gate fails closed. Move it to a reference "
                '(writer = "op://...") or lower the gate for this environment.'
            ),
        )

    # Drop any cached value so this fetch genuinely reaches the backend.
    credential.forget()
    credential.get()
    log.info("Writer credential for %s re-authorized for this invocation.", env)


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
