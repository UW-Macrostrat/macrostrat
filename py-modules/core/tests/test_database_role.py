"""Reader-by-default, and the gate as the only way to acquire write capability."""

from pytest import fixture, mark, raises

from macrostrat.core import database as db_module
from macrostrat.core import safety
from macrostrat.core.connections import DatabaseConnection, DatabaseRole
from macrostrat.core.environment import EnvironmentPolicy, WriteScope
from macrostrat.core.safety import WriteRefused, require_write_access
from macrostrat.core.secrets import RESOLVERS, forget_all_secrets, register_resolver

LITERAL = "postgresql://admin:admin-pw@localhost:5432/macrostrat"


@fixture(autouse=True)
def reset_ctx():
    """Each test starts as a fresh invocation would: no connection, Reader."""
    db_module.db_ctx.set(None)
    db_module.db_role_ctx.set(DatabaseRole.Reader)
    yield
    db_module.db_ctx.set(None)
    db_module.db_role_ctx.set(DatabaseRole.Reader)


@fixture
def stub_resolver():
    forget_all_secrets()
    register_resolver("stub", lambda body: f"pw-{body}")
    try:
        yield
    finally:
        RESOLVERS.pop("stub", None)
        forget_all_secrets()


class _Settings:
    def __init__(self, connection):
        self._connection = connection

    def database_url(self, role=DatabaseRole.Reader, name="macrostrat"):
        return self._connection.url(role)


def use_config(monkeypatch, *, literal=None, table=None):
    """Point the database module at a config shape."""
    monkeypatch.setattr(db_module, "PG_DATABASE", literal)
    if table is not None:
        monkeypatch.setattr(
            db_module, "settings", _Settings(DatabaseConnection.parse(table))
        )


def password_for_default_url():
    from sqlalchemy.engine import make_url

    url = db_module._default_database_url()
    return make_url(url).password if isinstance(url, str) else url.password


class TestDefaultIsReader:
    def test_a_fresh_invocation_is_a_reader(self):
        assert db_module.current_database_role() == DatabaseRole.Reader


class TestTheFlipIsANoOpForExistingConfigs:
    """Why this can land before the restricted reader role exists."""

    def test_a_literal_url_ignores_the_role_entirely(self, monkeypatch):
        use_config(monkeypatch, literal=LITERAL)
        as_reader = db_module._default_database_url()
        db_module.use_writer_connection()
        assert db_module._default_database_url() == as_reader == LITERAL

    def test_a_shared_password_resolves_the_same_for_both_roles(
        self, monkeypatch, stub_resolver
    ):
        use_config(
            monkeypatch,
            table={"host": "h", "database": "d", "password": "stub://shared"},
        )
        as_reader = password_for_default_url()
        db_module.use_writer_connection()
        assert password_for_default_url() == as_reader == "pw-shared"


class TestSplitCredentials:
    """The only shape where the flip changes anything."""

    TABLE = {
        "host": "h",
        "database": "d",
        "reader": "stub://reader",
        "writer": "stub://writer",
    }

    def test_reads_use_the_reader_credential(self, monkeypatch, stub_resolver):
        use_config(monkeypatch, table=self.TABLE)
        assert password_for_default_url() == "pw-reader"

    def test_escalation_switches_to_the_writer(self, monkeypatch, stub_resolver):
        use_config(monkeypatch, table=self.TABLE)
        db_module.use_writer_connection()
        assert db_module.current_database_role() == DatabaseRole.Writer
        assert password_for_default_url() == "pw-writer"


class _FakeDatabase:
    """Stands in for a live Database, recording teardown."""

    def __init__(self):
        self.closed = False
        self.disposed = False
        outer = self

        class _Session:
            def close(self):
                outer.closed = True

        class _Engine:
            def dispose(self):
                outer.disposed = True

        self.session = _Session()
        self.engine = _Engine()


class TestEscalationMechanics:
    def test_idempotent(self, monkeypatch):
        use_config(monkeypatch, literal=LITERAL)
        db_module.use_writer_connection()
        existing = _FakeDatabase()
        db_module.db_ctx.set(existing)
        db_module.use_writer_connection()  # already a writer
        # The live connection must not be torn down a second time.
        assert not existing.closed
        assert db_module.db_ctx.get() is existing

    def test_an_open_reader_connection_is_closed_and_dropped(self, monkeypatch):
        """A command that read before it asked to write must not keep reading."""
        use_config(monkeypatch, literal=LITERAL)
        existing = _FakeDatabase()
        db_module.db_ctx.set(existing)
        db_module.use_writer_connection()
        assert existing.closed and existing.disposed
        assert db_module.db_ctx.get() is None

    def test_a_failing_teardown_does_not_block_the_write(self, monkeypatch):
        """Losing a connection cleanly matters less than the authorized write."""
        use_config(monkeypatch, literal=LITERAL)

        class _Hostile(_FakeDatabase):
            def __init__(self):
                super().__init__()

                class _S:
                    def close(self):
                        raise RuntimeError("session already invalidated")

                self.session = _S()

        db_module.db_ctx.set(_Hostile())
        db_module.use_writer_connection()
        assert db_module.current_database_role() == DatabaseRole.Writer
        assert db_module.db_ctx.get() is None

    def test_no_open_connection_is_fine(self, monkeypatch):
        use_config(monkeypatch, literal=LITERAL)
        db_module.use_writer_connection()
        assert db_module.current_database_role() == DatabaseRole.Writer


class _PolicySettings:
    def __init__(self, policy):
        self.policy = policy

    def database_connection(self, name="macrostrat"):
        return None


def policy_settings(env, env_class):
    return _PolicySettings(EnvironmentPolicy.resolve(env, env_class=env_class))


class TestTheGateGrantsWriteCapability:
    @fixture
    def no_tty(self, monkeypatch):
        monkeypatch.setattr(safety, "is_interactive", lambda: False)

    def test_an_ungated_local_write_escalates(self, no_tty):
        """`local` is ungated but still writing — it must get a writer."""
        require_write_access(
            WriteScope.Data, settings=policy_settings("local", "local")
        )
        assert db_module.current_database_role() == DatabaseRole.Writer

    def test_confirm_with_yes_escalates(self, no_tty):
        require_write_access(
            WriteScope.Data,
            settings=policy_settings("development", "development"),
            assume_yes=True,
        )
        assert db_module.current_database_role() == DatabaseRole.Writer

    @mark.parametrize("env_class", ["development", "staging", "production"])
    def test_a_refused_gate_does_NOT_escalate(self, no_tty, env_class):
        """The property that matters: refusal must not grant write capability."""
        with raises(WriteRefused):
            require_write_access(
                WriteScope.Data, settings=policy_settings("env", env_class)
            )
        assert db_module.current_database_role() == DatabaseRole.Reader

    def test_escalation_can_be_declined_by_the_caller(self, no_tty):
        """A storage-only write should not acquire database write capability."""
        require_write_access(
            WriteScope.Data,
            settings=policy_settings("local", "local"),
            escalate_connection=False,
        )
        assert db_module.current_database_role() == DatabaseRole.Reader
