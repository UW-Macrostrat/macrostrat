"""`macrostrat db psql` resolves the reader credential, so it asks the read gate."""

from pytest import fixture, raises

from macrostrat.core import app, safety
from macrostrat.core import database as db_module
from macrostrat.core.connections import DatabaseConnection, DatabaseRole
from macrostrat.core.environment import EnvironmentPolicy
from macrostrat.core.safety import WriteRefused, resolve_database_url


class _GatedSettings:
    def __init__(self):
        self.policy = EnvironmentPolicy.resolve(
            "production", env_class="production", confirm={"read": "prompt"}
        )
        self._conn = DatabaseConnection.parse(
            {"host": "h", "database": "d", "password": "pw"}
        )

    def database_connection(self, name="macrostrat"):
        return self._conn

    def database_url(self, role=DatabaseRole.Reader, name="macrostrat"):
        return resolve_database_url(self, role, name)

    def get(self, key, default=None):
        return default


@fixture
def gated(monkeypatch):
    # A fresh invocation: other suites can leave this process escalated.
    db_module.db_ctx.set(None)
    db_module.db_role_ctx.set(DatabaseRole.Reader)
    safety._reads_confirmed.clear()
    monkeypatch.setattr(app, "settings", _GatedSettings())
    monkeypatch.setattr(safety, "is_interactive", lambda: False)
    yield
    safety._reads_confirmed.clear()
    db_module.db_role_ctx.set(DatabaseRole.Reader)


def test_psql_refuses_a_gated_read_without_a_terminal(gated, monkeypatch):
    from macrostrat.cli import database

    # Reaching docker would mean the gate was skipped.
    monkeypatch.setattr(
        database,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("psql started without passing the read gate")
        ),
    )
    with raises(WriteRefused):
        database.psql(None, write=False)
