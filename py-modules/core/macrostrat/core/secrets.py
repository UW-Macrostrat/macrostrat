"""Deferred resolution of secret references in configuration.

A config value may name a secret instead of containing one:

.. code-block:: toml

    [production.database]
    host   = "db.production.svc.macrostrat.org"
    reader = "op://Macrostrat Prod/macrostrat-db/reader/password"
    writer = "op://Macrostrat Prod/macrostrat-db/admin/password"

That keeps hosts and database names in plaintext — greppable, reviewable, and
genuinely useful context — while the secret half lives in a password manager, so
`macrostrat.toml` becomes committable.

Three properties matter, and they are why this is a module rather than a call to
``subprocess.run`` at the point of use:

**Resolution is deferred.** A reference resolves when something actually needs
the credential, not when config is loaded. Resolving at import would put a
1Password prompt in front of every ``macrostrat --help``, and would make the
whole scheme unusable in any non-interactive context.

**A resolved secret does not stringify.** :class:`Secret` redacts in ``repr``,
``str`` and every format context; the value comes out only through an explicit
:meth:`Secret.get`. `macrostrat db credentials` and `macrostrat self printenv`
have both historically printed live passwords, and ``--verbose`` logs
SQLAlchemy URLs. Making the value awkward to print by accident is worth more
than remembering to redact at each of those sites.

**Only registered schemes are references.** ``postgresql://user:pass@host/db``
is a URI too; it must pass through as the literal it is. A value is a reference
only if its scheme is in :data:`RESOLVERS`.

Resolvers are a protocol rather than a hard dependency on 1Password, so the
backend choice stays reversible and CI can use a different one.
"""

import re
from os import environ
from pathlib import Path
from shutil import which
from subprocess import DEVNULL, PIPE, run
from typing import Callable, Dict, Optional

from click.exceptions import ClickException

from macrostrat.utils import get_logger

log = get_logger(__name__)

#: Matches anything shaped like a URI. Having a scheme does *not* make a value a
#: secret reference — see :func:`is_secret_ref`.
_URI = re.compile(r"^(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*)://(?P<body>.*)$", re.DOTALL)

#: What a redacted secret renders as. Deliberately not the reference itself, so
#: that a leaked log line does not also disclose the vault layout.
REDACTED = "«redacted»"


class SecretResolutionError(RuntimeError, ClickException):
    """A secret reference could not be resolved, or a reveal was refused.

    Carries the *reference* and the backend's diagnostics — never the value.

    Also a `ClickException` so Click renders it as an error and exits 1 rather
    than letting it escape as a traceback. A refusal or a missing vault item
    that looks like a crash reads as "the tool is broken" rather than "you were
    stopped", and invites retrying harder.
    """

    exit_code = 1

    def __init__(self, message: str):
        RuntimeError.__init__(self, message)
        self.message = message

    def format_message(self) -> str:
        return self.message


class Secret:
    """A credential that has not been fetched yet, and will not stringify.

    Compares and hashes by reference, not by value, so a :class:`Secret` can sit
    in a dict or a set without being resolved.
    """

    __slots__ = ("_ref", "_scheme", "_body", "_cache", "_resolved")

    def __init__(self, ref: str, *, cache: bool = True):
        m = _URI.match(ref)
        if m is None or m.group("scheme").lower() not in RESOLVERS:
            raise ValueError(f"{ref!r} is not a recognized secret reference")
        self._ref = ref
        self._scheme = m.group("scheme").lower()
        self._body = m.group("body")
        #: Whether a resolved value may be held for the rest of the process.
        #: False for `escalate`-class credentials, which must be re-fetched —
        #: and so re-authorized — for every invocation that uses them.
        self._cache = cache
        self._resolved: Optional[str] = None

    @property
    def ref(self) -> str:
        """The reference itself. Safe to print — it names a secret, isn't one."""
        return self._ref

    @property
    def scheme(self) -> str:
        return self._scheme

    @property
    def cacheable(self) -> bool:
        return self._cache

    @property
    def is_resolved(self) -> bool:
        return self._resolved is not None

    def get(self) -> str:
        """Resolve and return the credential. The only path to the value."""
        if self._resolved is not None:
            return self._resolved
        value = RESOLVERS[self._scheme](self._body)
        if not value:
            raise SecretResolutionError(
                f"{self._ref} resolved to an empty value. "
                "Check that the item and field exist and are populated."
            )
        if self._cache:
            self._resolved = value
        return value

    def forget(self) -> None:
        """Drop any cached value, so the next :meth:`get` re-authorizes."""
        self._resolved = None

    # -- Everything below exists to keep the value out of output. ----------

    def __repr__(self) -> str:
        return f"Secret({self._ref!r})"

    def __str__(self) -> str:
        return REDACTED

    def __format__(self, spec: str) -> str:
        return REDACTED

    def __eq__(self, other) -> bool:
        return isinstance(other, Secret) and other._ref == self._ref

    def __hash__(self) -> int:
        return hash(("Secret", self._ref))

    def __bool__(self) -> bool:
        """True without resolving — a reference is a *promise* of a value."""
        return True


def is_secret_ref(value) -> bool:
    """Whether *value* names a secret in a backend we know how to talk to."""
    if not isinstance(value, str):
        return False
    m = _URI.match(value)
    return m is not None and m.group("scheme").lower() in RESOLVERS


#: Interned secrets, keyed by (reference, cacheable). One environment's reader
#: credential is typically shared by several databases; without interning, each
#: would build its own :class:`Secret` and fetch the same reference again — four
#: databases meant four `op read` calls, and so four biometric prompts, to open
#: four connections in a single invocation.
_INTERNED: Dict[tuple, "Secret"] = {}


def as_secret(value, *, cache: bool = True):
    """Wrap *value* in a :class:`Secret` if it is a reference, else return it.

    This is the compatibility hinge for the whole scheme: a literal password in
    a config file stays an ordinary ``str`` and behaves exactly as it does
    today. Only a value that names a registered backend changes shape.

    References are interned, so the same reference resolves once per process
    however many places name it. Note that a ``cache=False`` secret is still
    shared, but re-resolves on every :meth:`Secret.get` by construction — so a
    single invocation touching several databases through one uncached
    credential still fetches it once per use.
    """
    if not is_secret_ref(value):
        return value
    key = (value, cache)
    secret = _INTERNED.get(key)
    if secret is None:
        secret = Secret(value, cache=cache)
        _INTERNED[key] = secret
    return secret


def forget_all_secrets() -> None:
    """Drop every interned secret and its cached value.

    For tests, and for any caller that wants the next resolution to
    re-authorize from scratch.
    """
    for secret in _INTERNED.values():
        secret.forget()
    _INTERNED.clear()


def reveal(value) -> Optional[str]:
    """The plain value of *value*, resolving it if it is a :class:`Secret`."""
    if isinstance(value, Secret):
        return value.get()
    if value is None:
        return None
    return str(value)


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------


def resolve_onepassword(body: str) -> str:
    """Resolve ``op://vault/item[/section]/field`` via the 1Password CLI.

    Uses `op`'s own URI syntax rather than a scheme of our own, so the vendor
    tooling (`op read`, `op inject`) works against the same references. Vault
    ACLs — not this code — are what keep a dev-scoped credential from reaching
    production, and `op`'s biometric/approval unlock is the human-presence check
    that an `escalate` gate depends on.
    """
    if which("op") is None:
        raise SecretResolutionError(
            "op:// reference found but the 1Password CLI (`op`) is not on PATH. "
            "Install it (https://developer.1password.com/docs/cli/) or point "
            "this environment at a different resolver."
        )
    ref = f"op://{body}"
    proc = run(
        ["op", "read", "--no-newline", ref],
        stdout=PIPE,
        stderr=PIPE,
        stdin=DEVNULL,
        text=True,
    )
    if proc.returncode != 0:
        # `op` reports the reference and the reason, not the value.
        detail = (proc.stderr or "").strip().splitlines()
        raise SecretResolutionError(
            f"`op read` failed for {ref} (exit {proc.returncode}): "
            + (detail[-1] if detail else "no diagnostics")
        )
    return proc.stdout


def resolve_env(body: str) -> str:
    """Resolve ``env://VAR_NAME`` from the process environment.

    The backend for CI and for cloud agent sessions, which have no TTY and no
    `op` session: a scoped, reader-only service credential is injected as an
    environment variable. It is *not* a good backend for a writer credential —
    anything in the environment is inherited by every subprocess.
    """
    name = body.strip()
    try:
        return environ[name]
    except KeyError:
        raise SecretResolutionError(
            f"env://{name} is not set in the environment."
        ) from None


def resolve_file(body: str) -> str:
    """Resolve ``file:///path/to/secret`` by reading the file.

    For Kubernetes secret mounts and Docker secrets, where the platform has
    already placed the credential on disk.
    """
    path = Path(body).expanduser()
    try:
        return path.read_text().rstrip("\n")
    except OSError as err:
        raise SecretResolutionError(
            f"file://{path} could not be read: {err.strerror}"
        ) from None


def resolve_keychain(body: str) -> str:
    """Resolve ``keychain://service/account`` from the macOS keychain."""
    if which("security") is None:
        raise SecretResolutionError(
            "keychain:// references are only supported on macOS "
            "(`security` is not on PATH)."
        )
    service, _, account = body.partition("/")
    if not service or not account:
        raise SecretResolutionError(
            f"keychain://{body} is malformed; expected keychain://service/account."
        )
    proc = run(
        ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
        stdout=PIPE,
        stderr=PIPE,
        stdin=DEVNULL,
        text=True,
    )
    if proc.returncode != 0:
        raise SecretResolutionError(
            f"No keychain item for service {service!r}, account {account!r}."
        )
    return proc.stdout.rstrip("\n")


#: Scheme → resolver. A scheme absent from this table is not a secret
#: reference, which is what keeps `postgresql://` URLs passing through as the
#: literals they are.
RESOLVERS: Dict[str, Callable[[str], str]] = {
    "op": resolve_onepassword,
    "env": resolve_env,
    "file": resolve_file,
    "keychain": resolve_keychain,
}


def register_resolver(scheme: str, resolver: Callable[[str], str]) -> None:
    """Register a backend for *scheme*, so the choice stays reversible."""
    RESOLVERS[scheme.lower()] = resolver


# ---------------------------------------------------------------------------
# Redaction for commands that print configuration
# ---------------------------------------------------------------------------

#: Variable-name fragments that mark a value as a credential. Deliberately
#: broad: over-redacting a harmless variable costs a `--reveal`, while
#: under-redacting one puts a live credential in a transcript.
_SENSITIVE_NAME = re.compile(
    r"(PASSW|PASSWD|SECRET|TOKEN|CREDENTIAL|PRIVATE|SESSION|_KEY|KEY_|^KEY$|AUTH)",
    re.IGNORECASE,
)


def is_sensitive_name(name: str) -> bool:
    """Whether a variable's *name* suggests it holds a credential."""
    return bool(_SENSITIVE_NAME.search(str(name)))


def resolved_secret_values() -> set:
    """Every secret value resolved so far in this process.

    Used to redact by *value* as well as by name, which catches a credential
    embedded in something innocuously named — a connection URL, most obviously.
    """
    return {
        secret._resolved
        for secret in _INTERNED.values()
        if secret._resolved is not None
    }


#: A credential embedded in a URL's userinfo — `scheme://user:password@host`.
#: Matched structurally rather than by name, because the variable holding one is
#: often innocuously named: `MACROSTRAT_DATABASE_URL` carries a live password and
#: contains none of the words in :data:`_SENSITIVE_NAME`. Value-matching against
#: resolved secrets does not catch it either, since a literal password in a
#: config file never passes through :class:`Secret`.
_URL_PASSWORD = re.compile(
    r"(?P<pre>[A-Za-z][A-Za-z0-9+.\-]*://[^:/?#\s@]+:)(?P<pw>[^@/?#\s]+)(?P<post>@)"
)


def redact_url_passwords(text: str) -> str:
    """Mask the password in every `scheme://user:password@host` in *text*."""
    return _URL_PASSWORD.sub(
        lambda m: m.group("pre") + REDACTED + m.group("post"), str(text)
    )


def redact_text(text: str) -> str:
    """Redact secrets in *text* — resolved values, and URL-embedded passwords."""
    out = str(text)
    for value in resolved_secret_values():
        if value and value in out:
            out = out.replace(value, REDACTED)
    return redact_url_passwords(out)


def redact_mapping(mapping) -> dict:
    """*mapping* with credential-ish entries replaced by :data:`REDACTED`.

    An entry is redacted when its name looks sensitive **or** its value
    contains a secret this process has resolved.
    """
    out = {}
    for key, value in dict(mapping).items():
        if is_sensitive_name(key):
            out[key] = REDACTED
        else:
            out[key] = redact_text(value)
    return out


def refuse_non_interactive_reveal(what: str = "this value") -> None:
    """Raise unless a human is plausibly present at a terminal.

    Revealing a credential writes it to output that is routinely captured — a
    log, a CI artifact, an agent transcript. An agent has no TTY, so this is
    the cheapest available check that a person asked. It is *not* a substitute
    for the write gates: it stops an accident, not an attacker.
    """
    import sys

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise SecretResolutionError(
            f"Refusing to reveal {what} without an interactive terminal. "
            "Run this from a terminal if you need the plain value."
        )
