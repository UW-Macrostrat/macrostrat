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

from enum import Enum
from typing import Any, Mapping, Optional

from pydantic import BaseModel, ConfigDict

from macrostrat.utils import get_logger

log = get_logger(__name__)

#: TOML key declaring an environment's class. Deliberately **not** ``class``,
#: which is a Python keyword and would only ever be reachable via ``getattr``.
ENV_CLASS_KEY = "env_class"

#: TOML key holding per-scope gate overrides.
WRITE_GATE_KEY = "write_gate"

#: The name Dynaconf treats as the shared base layer rather than a selectable
#: environment.
DEFAULT_ENV = "default"

#: The only environment name assumed local when it declares no class.
LOCAL_ENV = "local"


class EnvironmentClass(str, Enum):
    """How expensive it should be to write to an environment."""

    Local = "local"
    Development = "development"
    Staging = "staging"
    Production = "production"


class WriteScope(str, Enum):
    """The kind of change a command makes.

    There is deliberately no ``services`` scope. The original plan had one for
    ``up`` / ``down`` / ``restart``, but those manage the **local** compose
    stack only — there is nothing there to protect, and the one remote
    subsystem (``kubernetes``) exposes no write command. A scope with no
    members is worse than no scope: it renders a column in
    `macrostrat config environments` that looks enforced and is not. Re-add it
    if deploy commands ever land.
    """

    #: Row-level changes: ingestion, restores, deletions.
    Data = "data"
    #: DDL: schema application, migrations, topology table drops.
    Schema = "schema"


class WriteGate(str, Enum):
    """What a caller must do to obtain write capability."""

    #: Proceed.
    NoGate = "none"
    #: ``y/N`` prompt; refuse when non-interactive unless explicitly allowed.
    Confirm = "confirm"
    #: Type the environment name. Always refuses when non-interactive.
    Typed = "typed"
    #: ``Typed``, plus the write credential must be fetched fresh from the
    #: secret manager for this invocation. No cached credential, no bypass.
    Escalate = "escalate"

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


#: Default gate per (class, scope). An environment declaring only a class gets
#: the row for that class.
DEFAULT_GATES: Mapping[EnvironmentClass, Mapping[WriteScope, WriteGate]] = {
    EnvironmentClass.Local: {
        WriteScope.Data: WriteGate.NoGate,
        WriteScope.Schema: WriteGate.NoGate,
    },
    EnvironmentClass.Development: {
        WriteScope.Data: WriteGate.Confirm,
        WriteScope.Schema: WriteGate.Confirm,
    },
    EnvironmentClass.Staging: {
        WriteScope.Data: WriteGate.Typed,
        WriteScope.Schema: WriteGate.Typed,
    },
    EnvironmentClass.Production: {
        WriteScope.Data: WriteGate.Escalate,
        WriteScope.Schema: WriteGate.Escalate,
    },
}


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
    ) -> "EnvironmentPolicy":
        """Build a policy from an environment's two declared values.

        Pure: no settings object, no I/O. ``env_class`` and ``write_gate`` are
        whatever the config file held, including ``None`` and junk.
        """
        resolved, inferred, reason = _resolve_class(name, env_class)
        gates = dict(DEFAULT_GATES[resolved])
        gates.update(_parse_gate_overrides(name, write_gate))
        return cls(
            name=name,
            env_class=resolved,
            gates=gates,
            inferred=inferred,
            reason=reason,
        )


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


def _parse_gate_overrides(
    name: Optional[str], write_gate: Optional[Mapping[str, Any]]
) -> dict:
    """Parse a ``[env.write_gate]`` table, ignoring what we can't understand."""
    if not write_gate:
        return {}
    if not hasattr(write_gate, "items"):
        log.warning(
            "Environment %r has a %s that is not a table (%r); ignoring it.",
            name,
            WRITE_GATE_KEY,
            write_gate,
        )
        return {}

    out = {}
    for scope, gate in write_gate.items():
        try:
            out[WriteScope(str(scope).strip().lower())] = WriteGate(
                str(gate).strip().lower()
            )
        except ValueError:
            log.warning(
                "Environment %r declares an unrecognized gate %s.%s = %r; "
                "ignoring it and keeping the class default.",
                name,
                WRITE_GATE_KEY,
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
    )
