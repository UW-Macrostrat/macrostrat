"""Plugins register through a small host interface, and never break the CLI."""

from types import SimpleNamespace

from typer import Typer

from macrostrat.core import plugins
from macrostrat.core.plugins import HostContext, load_plugins


class FakeEntryPoint:
    def __init__(self, name, register):
        self.name = name
        self.value = f"fake:{name}"
        self.dist = SimpleNamespace(name=f"fake-{name}", version="0.1")
        self._register = register

    def load(self):
        return self._register


def _install(monkeypatch, *eps):
    monkeypatch.setattr(plugins, "entry_points", lambda group: list(eps))


def _host():
    return HostContext(main_app=Typer(), db_app=Typer())


def test_a_plugin_adds_commands(monkeypatch):
    def register(host):
        host.db_app.command(name="copy")(lambda: None)

    _install(monkeypatch, FakeEntryPoint("cluster", register))
    host = _host()

    [status] = load_plugins(host)

    assert status.error is None
    assert status.distribution == "fake-cluster 0.1"
    assert [c.name for c in host.db_app.registered_commands] == ["copy"]


def test_a_broken_plugin_is_reported_not_raised(monkeypatch):
    def broken(host):
        raise ImportError("no module named kubernetes")

    def fine(host):
        host.main_app.command(name="ok")(lambda: None)

    _install(monkeypatch, FakeEntryPoint("broken", broken), FakeEntryPoint("ok", fine))
    host = _host()

    statuses = load_plugins(host)

    assert statuses[0].error == "ImportError: no module named kubernetes"
    assert statuses[1].error is None
    assert [c.name for c in host.main_app.registered_commands] == ["ok"]


def test_gates_use_the_named_environment_and_never_escalate(monkeypatch):
    import macrostrat.core.database as database
    import macrostrat.core.safety as safety

    named = SimpleNamespace(name="production")
    calls = []
    monkeypatch.setattr(database, "_settings_for_env", lambda env: named)
    monkeypatch.setattr(
        safety, "require_write_access", lambda scope, **kw: calls.append((scope, kw))
    )

    _host().require_write("schema", "production", action="copy", assume_yes=True)

    [(scope, kw)] = calls
    assert scope.value == "schema"
    assert kw["settings"] is named
    assert kw["escalate_connection"] is False
    assert kw["assume_yes"] is True
