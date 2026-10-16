"""Plugins: packages that add CLI commands from outside this repository.

A plugin is an entry point in the ``macrostrat.plugins`` group naming a function
``register(host: HostContext)``. It gets this small interface instead of the
CLI's internals, so it can live in another repository — the cluster tooling in
tiger-macrostrat-config is the first — and be installed beside the CLI by a
composition root such as macrostrat-pyroot. Plugins import this module only for
type checking.
"""

from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from typer import Typer

#: Raised only for additive changes; a plugin checks ``host.api_version >= N``.
API_VERSION = 1

ENTRY_POINT_GROUP = "macrostrat.plugins"


@dataclass(frozen=True)
class EnvironmentView:
    """What a plugin may know about a `macrostrat.toml` environment."""

    name: str
    env_class: str


class HostContext:
    """The CLI as a plugin sees it: where to add commands, and its safety gates."""

    api_version = API_VERSION

    def __init__(self, main_app: "Typer", db_app: "Typer"):
        self.main_app = main_app
        self.db_app = db_app

    def environment(self, name: str) -> EnvironmentView:
        policy = _settings(name).policy
        return EnvironmentView(name=name, env_class=policy.env_class.value)

    def require_read(self, env: str, *, action: str) -> None:
        from .safety import require_read_access

        require_read_access(settings=_settings(env), action=action)

    def require_write(
        self, scope: str, env: str, *, action: str, assume_yes: bool = False
    ) -> None:
        from .environment import WriteScope
        from .safety import require_write_access

        # Never escalate: a plugin does not use this invocation's connection.
        require_write_access(
            WriteScope(scope),
            settings=_settings(env),
            assume_yes=assume_yes,
            action=action,
            escalate_connection=False,
        )


def _settings(env: str):
    from .database import _settings_for_env

    return _settings_for_env(env)


@dataclass
class PluginStatus:
    name: str
    target: str
    distribution: Optional[str] = None
    error: Optional[str] = None


def load_plugins(host: HostContext) -> list[PluginStatus]:
    """Register every installed plugin; a failure is reported, never raised."""
    statuses = []
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        dist = f"{ep.dist.name} {ep.dist.version}" if ep.dist else None
        status = PluginStatus(name=ep.name, target=ep.value, distribution=dist)
        try:
            ep.load()(host)
        except Exception as err:
            status.error = f"{type(err).__name__}: {err}"
        statuses.append(status)
    return statuses
