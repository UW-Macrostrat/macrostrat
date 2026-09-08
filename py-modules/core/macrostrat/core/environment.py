"""Environment classification and write gating.

Every Macrostrat environment is read/write at some level; what differs is how
expensive it *should* be to obtain write capability, and in what scope. So an
environment declares a **class** and, optionally, a per-scope **write gate** —
not a read-only flag:

.. code-block:: toml

    [production]
    env_class = "production"

    [production.write_gate]
    data = "typed"            # override the class default

Each class ships a default gate table, so a normal environment declares only
``env_class``. An environment that declares no class is assumed to be
``production`` unless it is named ``local`` — fail closed, loudly.

This module is deliberately free of side effects and of any dependency on the
settings object: :meth:`EnvironmentPolicy.resolve` is a pure function of the two
declared values, and :func:`policy_from_settings` is a thin adapter over it.

See the workbench note "System configuration safety" for the design rationale.
"""

import re
from datetime import timedelta
from enum import Enum
from typing import Any, Mapping, Optional

from pydantic import BaseModel, ConfigDict

from macrostrat.utils import get_logger

log = get_logger(__name__)

#: TOML key declaring an environment's class. Deliberately **not** ``class``,
#: which is a Python keyword and would only ever be reachable via ``getattr``.
ENV_CLASS_KEY = "env_class"

#: TOML key holding per-scope gate overrides (config version 1).
WRITE_GATE_KEY = "write_gate"

#: TOML key holding per-scope confirmation levels (config version 2): a table
#: ``{ read = …, data = …, schema = … }``, or one level applied to both kinds
#: of write.
CONFIRM_KEY = "confirm"

#: TOML key overriding how long `macrostrat env <name>` keeps this environment
#: active. A duration (``"15m"``, ``"8h"``, ``"2h30m"``, a bare number of
#: minutes) or ``"never"``. Absent, the class default applies.
ACTIVE_TTL_KEY = "active_ttl"

#: The name Dynaconf treats as the shared base layer rather than a selectable
#: environment.
DEFAULT_ENV = "default"

#: The only environment name assumed local when it declares no class.
LOCAL_ENV = "local"


class EnvironmentClass(str, Enum):
    """Where an environment sits on the scale from a laptop to production.

    One vocabulary for two things: how expensive a write should be (the
    default confirmation levels below), and which schema layers apply — the
    development-only definitions run in ``local`` and ``development``, the
    local seed data in ``local`` only. See :func:`classes_up_to`.
    """

    Local = "local"
    Development = "development"
    Staging = "staging"
    Production = "production"

    @property
    def rank(self) -> int:
        """Position on the scale: local 0 … production 3."""
        return _CLASS_ORDER.index(self)


_CLASS_ORDER = (
    EnvironmentClass.Local,
    EnvironmentClass.Development,
    EnvironmentClass.Staging,
    EnvironmentClass.Production,
)


def classes_up_to(top: EnvironmentClass) -> frozenset:
    """Every class from ``local`` up to and including *top*.

    ``classes_up_to(Development)`` is ``{local, development}`` — the set a
    development-only schema layer applies in.
    """
    top = EnvironmentClass(top)
    return frozenset(c for c in _CLASS_ORDER if c.rank <= top.rank)


class WriteScope(str, Enum):
    """The kind of database access a command needs.

    ``Read`` is here so that an environment can ask before *any* connection is
    opened — a production database where even looking should be deliberate.
    It is ungated by default in every class.

    There is deliberately no ``services`` scope. The original plan had one for
    ``up`` / ``down`` / ``restart``, but those manage the **local** compose
    stack only — there is nothing there to protect, and the one remote
    subsystem (``kubernetes``) exposes no write command. A scope with no
    members is worse than no scope: it renders a column in
    `macrostrat config environments` that looks enforced and is not. Re-add it
    if deploy commands ever land.
    """

    #: Opening a connection at all.
    Read = "read"
    #: Row-level changes: ingestion, restores, deletions.
    Data = "data"
    #: DDL: schema application, migrations, topology table drops.
    Schema = "schema"


#: The two kinds of write, in the order they appear in tables.
WRITE_SCOPES = (WriteScope.Data, WriteScope.Schema)


class WriteGate(str, Enum):
    """What a person must do before the access proceeds.

    The levels form a ladder; each includes the ones below it. The values are
    the words a config file uses; :func:`parse_gate` also accepts the earlier
    spellings (``confirm``, ``typed``, ``escalate``) and TOML booleans.
    """

    #: Proceed.
    NoGate = "none"
    #: A ``y/N`` prompt; refused when non-interactive unless ``--yes`` is given.
    Confirm = "prompt"
    #: Type the environment's name. Always refused when non-interactive.
    Typed = "environment-name"
    #: Type the name, and the credential is fetched fresh from the secret
    #: manager for this invocation, so its approval prompt is in the path.
    Escalate = "reauthorize"

    @property
    def severity(self) -> int:
        """Position in the ordering, so gates can be compared and maxed."""
        return _GATE_SEVERITY[self]


_GATE_SEVERITY = {
    WriteGate.NoGate: 0,
    WriteGate.Confirm: 1,
    WriteGate.Typed: 2,
    WriteGate.Escalate: 3,
}

#: Every spelling a config may use for a level. The current words first; the
#: version-1 words and plain booleans after, so an older file keeps working.
GATE_SPELLINGS: Mapping[str, WriteGate] = {
    "none": WriteGate.NoGate,
    "false": WriteGate.NoGate,
    "off": WriteGate.NoGate,
    "no": WriteGate.NoGate,
    "prompt": WriteGate.Confirm,
    "confirm": WriteGate.Confirm,
    "true": WriteGate.Confirm,
    "yes": WriteGate.Confirm,
    "environment-name": WriteGate.Typed,
    "environment_name": WriteGate.Typed,
    "typed": WriteGate.Typed,
    "reauthorize": WriteGate.Escalate,
    "escalate": WriteGate.Escalate,
}


def parse_gate(value: Any) -> WriteGate:
    """A level from a config value: a word above, or a TOML boolean."""
    if isinstance(value, WriteGate):
        return value
    if isinstance(value, bool):
        return WriteGate.Confirm if value else WriteGate.NoGate
    key = str(value).strip().lower()
    if key not in GATE_SPELLINGS:
        raise ValueError(
            f"{value!r} is not a confirmation level; use one of "
            + ", ".join(g.value for g in WriteGate)
        )
    return GATE_SPELLINGS[key]


#: Default gate per (class, scope). An environment declaring only a class gets
#: the row for that class.
DEFAULT_GATES: Mapping[EnvironmentClass, Mapping[WriteScope, WriteGate]] = {
    EnvironmentClass.Local: {
        WriteScope.Read: WriteGate.NoGate,
        WriteScope.Data: WriteGate.NoGate,
        WriteScope.Schema: WriteGate.NoGate,
    },
    EnvironmentClass.Development: {
        WriteScope.Read: WriteGate.NoGate,
        WriteScope.Data: WriteGate.Confirm,
        WriteScope.Schema: WriteGate.Confirm,
    },
    EnvironmentClass.Staging: {
        WriteScope.Read: WriteGate.NoGate,
        WriteScope.Data: WriteGate.Typed,
        WriteScope.Schema: WriteGate.Typed,
    },
    EnvironmentClass.Production: {
        WriteScope.Read: WriteGate.NoGate,
        WriteScope.Data: WriteGate.Escalate,
        WriteScope.Schema: WriteGate.Escalate,
    },
}


#: Default time-to-live for a *remembered* environment, per class. `local` never
#: lapses. The rest lapse on a scale matched to how long a task there plausibly
#: takes and how bad a forgotten pointer is: a day's work on development, an
#: hour on staging, a quarter-hour on production. A lapsed environment is not
#: dropped — it is kept and the operator is asked before it is used again.
DEFAULT_TTL: Mapping[EnvironmentClass, Optional[timedelta]] = {
    EnvironmentClass.Local: None,
    EnvironmentClass.Development: timedelta(hours=8),
    EnvironmentClass.Staging: timedelta(hours=1),
    EnvironmentClass.Production: timedelta(minutes=15),
}

_NEVER = {"never", "none", "off", "infinite", "indefinite", "forever"}
_DURATION = re.compile(
    r"^\s*(?:(?P<d>\d+)\s*d)?\s*(?:(?P<h>\d+)\s*h)?\s*(?:(?P<m>\d+)\s*m(?:in)?)?"
    r"\s*(?:(?P<s>\d+)\s*s)?\s*$",
    re.IGNORECASE,
)


class InvalidDuration(ValueError):
    """A TTL that could not be understood."""


def parse_duration(value: Any) -> Optional[timedelta]:
    """Parse a TTL: ``"15m"``, ``"8h"``, ``"2h30m"``, ``"1d"``, ``90`` (minutes),
    or ``"never"`` for no expiry. ``None`` means "not declared" and is returned
    as-is so the caller can apply a default.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        if value is False:
            return None
        raise InvalidDuration(f"{value!r} is not a duration")
    if isinstance(value, timedelta):
        return value
    if isinstance(value, (int, float)):
        if value <= 0:
            raise InvalidDuration(f"{value!r} is not a positive duration")
        return timedelta(minutes=float(value))
    text = str(value).strip().lower()
    if text in _NEVER:
        return None
    if text.isdigit():
        return timedelta(minutes=int(text))
    m = _DURATION.match(text)
    if m is None or not any(m.groupdict().values()):
        raise InvalidDuration(
            f"{value!r} is not a duration; use e.g. 15m, 8h, 2h30m, 1d, or never"
        )
    parts = {k: int(v) for k, v in m.groupdict().items() if v is not None}
    out = timedelta(
        days=parts.get("d", 0),
        hours=parts.get("h", 0),
        minutes=parts.get("m", 0),
        seconds=parts.get("s", 0),
    )
    if out <= timedelta(0):
        raise InvalidDuration(f"{value!r} is not a positive duration")
    return out


def format_duration(value: Optional[timedelta]) -> str:
    """``timedelta`` → ``"15 min"``, ``"8 h"``, ``"2 h 30 min"``, ``"never"``."""
    if value is None:
        return "never"
    total = int(value.total_seconds())
    if total < 60:
        return f"{total} s"
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    parts = []
    if days:
        parts.append(f"{days} d")
    if hours:
        parts.append(f"{hours} h")
    if minutes:
        parts.append(f"{minutes} min")
    return " ".join(parts)


class EnvironmentPolicy(BaseModel):
    """The resolved safety policy for one environment."""

    model_config = ConfigDict(frozen=True)

    #: Environment name, or ``None`` when no environment is selected.
    name: Optional[str]
    env_class: EnvironmentClass
    gates: Mapping[WriteScope, WriteGate]
    #: True when ``env_class`` was *not* declared and had to be inferred.
    inferred: bool = False
    #: Human-readable account of how the class was arrived at.
    reason: str = "declared"
    #: How long `macrostrat env <name>` keeps this environment active before the
    #: operator is asked again. ``None`` means it never lapses.
    ttl: Optional[timedelta] = None

    @property
    def is_local(self) -> bool:
        return self.env_class == EnvironmentClass.Local

    def gate_for(self, scope: WriteScope) -> WriteGate:
        """The gate guarding *scope* in this environment."""
        return self.gates[WriteScope(scope)]

    @classmethod
    def resolve(
        cls,
        name: Optional[str],
        env_class: Any = None,
        write_gate: Optional[Mapping[str, Any]] = None,
        active_ttl: Any = None,
        confirm: Any = None,
    ) -> "EnvironmentPolicy":
        """Build a policy from an environment's declared values.

        Pure: no settings object, no I/O. ``env_class``, ``write_gate``,
        ``confirm`` and ``active_ttl`` are whatever the config file held,
        including ``None`` and junk. ``confirm`` (version 2) and ``write_gate``
        (version 1) both override the class defaults; a file has one of them.
        """
        resolved, inferred, reason = _resolve_class(name, env_class)
        gates = dict(DEFAULT_GATES[resolved])
        gates.update(_parse_gate_overrides(name, write_gate))
        gates.update(_parse_confirm(name, confirm))
        return cls(
            name=name,
            env_class=resolved,
            gates=gates,
            inferred=inferred,
            reason=reason,
            ttl=_resolve_ttl(name, resolved, active_ttl),
        )


def _resolve_ttl(
    name: Optional[str], env_class: EnvironmentClass, declared: Any
) -> Optional[timedelta]:
    """The declared TTL, or the class default when absent or unparseable."""
    default = DEFAULT_TTL[env_class]
    if declared is None:
        return default
    try:
        return parse_duration(declared)
    except InvalidDuration as err:
        log.warning(
            "Environment %r declares %s = %r (%s); using the %s default of %s.",
            name,
            ACTIVE_TTL_KEY,
            declared,
            err,
            env_class.value,
            format_duration(default),
        )
        return default


def _resolve_class(name: Optional[str], declared: Any) -> tuple:
    """Resolve an environment's class, failing closed on anything unclear."""
    if declared is not None:
        try:
            return EnvironmentClass(str(declared).strip().lower()), False, "declared"
        except ValueError:
            log.warning(
                "Environment %r declares unknown %s=%r; treating it as %s. "
                "Valid classes: %s.",
                name,
                ENV_CLASS_KEY,
                declared,
                EnvironmentClass.Production.value,
                ", ".join(c.value for c in EnvironmentClass),
            )
            return (
                EnvironmentClass.Production,
                True,
                f"unknown {ENV_CLASS_KEY}={declared!r}, failed closed",
            )

    # Nothing declared. `local` is the one name we trust; everything else — an
    # unnamed environment included — is assumed to be the most dangerous thing
    # it could be.
    if name == LOCAL_ENV:
        return EnvironmentClass.Local, True, f"named {LOCAL_ENV!r}"

    if name is None:
        # Debug, not a warning: no environment selected means no operation is
        # in flight either, and this is the state of every `macrostrat --help`
        # on a machine with no config. The class still fails closed, so
        # anything that *does* try to write gets the strictest gate.
        log.debug(
            "No environment is selected, so no safety policy could be resolved; "
            "assuming %s.",
            EnvironmentClass.Production.value,
        )
        return (
            EnvironmentClass.Production,
            True,
            "no environment selected, failed closed",
        )

    log.warning(
        "Environment %r declares no %s, so it is treated as %s. Add "
        '%s = "..." to its section in macrostrat.toml to say what it really is.',
        name,
        ENV_CLASS_KEY,
        EnvironmentClass.Production.value,
        ENV_CLASS_KEY,
    )
    return (
        EnvironmentClass.Production,
        True,
        f"no {ENV_CLASS_KEY} declared, failed closed",
    )


def _parse_confirm(name: Optional[str], confirm: Any) -> dict:
    """Parse ``confirm``: a table per scope, or one level for both writes.

    A scalar applies to ``data`` and ``schema`` only. Reads are never gated by
    implication; an environment that wants to ask before reads says so.
    """
    if confirm is None:
        return {}
    if not hasattr(confirm, "items"):
        try:
            level = parse_gate(confirm)
        except ValueError as err:
            log.warning(
                "Environment %r: %s = %r ignored (%s).", name, CONFIRM_KEY, confirm, err
            )
            return {}
        return {scope: level for scope in WRITE_SCOPES}
    return _parse_gate_overrides(name, confirm, key=CONFIRM_KEY)


def _parse_gate_overrides(
    name: Optional[str],
    write_gate: Optional[Mapping[str, Any]],
    key: str = WRITE_GATE_KEY,
) -> dict:
    """Parse a per-scope table, ignoring what we can't understand."""
    if not write_gate:
        return {}
    if not hasattr(write_gate, "items"):
        log.warning(
            "Environment %r has a %s that is not a table (%r); ignoring it.",
            name,
            key,
            write_gate,
        )
        return {}

    out = {}
    for scope, gate in write_gate.items():
        try:
            out[WriteScope(str(scope).strip().lower())] = parse_gate(gate)
        except ValueError:
            log.warning(
                "Environment %r declares an unrecognized level %s.%s = %r; "
                "ignoring it and keeping the class default.",
                name,
                key,
                scope,
                gate,
            )
    return out


def policy_from_settings(settings) -> EnvironmentPolicy:
    """Resolve the active environment's policy from a settings object."""
    name = getattr(settings, "env", None)
    if name == DEFAULT_ENV:
        # `default` is the base layer, never a selectable environment.
        name = None
    return EnvironmentPolicy.resolve(
        name,
        env_class=settings.get(ENV_CLASS_KEY, None),
        write_gate=settings.get(WRITE_GATE_KEY, None),
        active_ttl=settings.get(ACTIVE_TTL_KEY, None),
        confirm=settings.get(CONFIRM_KEY, None),
    )


def declared_policy_for(config_file, env_name: Optional[str]) -> EnvironmentPolicy:
    """Resolve *env_name*'s policy by reading the TOML directly.

    Deliberately bypasses Dynaconf. Deciding whether a *persisted* active
    environment may still be used has to happen **before** settings are
    constructed — and constructing settings requires already knowing which
    environment is active. Reading the raw file breaks that circularity.

    Goes through :meth:`EnvironmentPolicy.resolve`, so it cannot disagree with
    the policy the loaded settings will produce. An unreadable or absent
    section yields the same fail-closed answer as a missing `env_class`.
    """
    table = {}
    if config_file is not None and env_name is not None:
        try:
            from toml import load as load_toml

            with open(config_file) as f:
                table = load_toml(f).get(env_name, None) or {}
        except (OSError, ValueError, TypeError):
            log.debug("Could not read %r from %s", env_name, config_file)
            table = {}
    if not hasattr(table, "get"):
        table = {}
    return EnvironmentPolicy.resolve(
        env_name,
        env_class=table.get(ENV_CLASS_KEY, None),
        write_gate=table.get(WRITE_GATE_KEY, None),
        active_ttl=table.get(ACTIVE_TTL_KEY, None),
        confirm=table.get(CONFIRM_KEY, None),
    )
