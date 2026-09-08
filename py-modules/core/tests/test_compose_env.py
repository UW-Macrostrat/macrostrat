"""Command-time export of what the local compose stack reads."""

from pytest import fixture

from macrostrat.core.compose_env import (
    COMPOSE_COMMANDS,
    DATABASE_VARIABLES,
    export_compose_environment,
)
from macrostrat.core.connections import DatabaseRole, connections_for
from macrostrat.core.secrets import (
    RESOLVERS,
    SecretResolutionError,
    forget_all_secrets,
    register_resolver,
)
from macrostrat.core.storage import StorageEndpoint

LOCAL = "postgresql://admin:local-pw@localhost:5433/macrostrat"
ELEVATION = "postgresql://elev:elev-pw@db.development.svc:5432/elevation"


@fixture
def resolvers():
    """`stub://` resolves; `broken://` never does."""
    forget_all_secrets()
    values = {"elevation-url": ELEVATION, "key": "signing-key", "sk": "s3-secret"}
    register_resolver("stub", lambda body: values[body])

    def fail(body):
        raise SecretResolutionError(f"cannot reach {body}")

    register_resolver("broken", fail)
    try:
        yield
    finally:
        RESOLVERS.pop("stub", None)
        RESOLVERS.pop("broken", None)
        forget_all_secrets()


class _Settings(dict):
    """The slice of `MacrostratConfig` the exporter touches."""

    def get(self, key, default=None):
        return super().get(key, default)

    def database_connection(self, name="macrostrat"):
        return connections_for(self).get(name)

    def resolve_token_signing_key(self):
        from macrostrat.core.secrets import as_secret, reveal

        return reveal(as_secret(self.get("token_signing_key")))

    def storage_endpoint(self, name="default"):
        storage = self.get("storage")
        if storage is None:
            return None
        return StorageEndpoint.parse(storage)


def vaulted_settings(**overrides):
    base = dict(
        database={
            "host": "localhost",
            "port": 5433,
            "user": "admin",
            "password": "local-pw",
        },
        databases={"elevation": "stub://elevation-url"},
        token_signing_key="stub://key",
        storage={
            "endpoint": "localhost:9000",
            "access_key": "ak",
            "secret_key": "stub://sk",
        },
    )
    base.update(overrides)
    return _Settings(base)


def test_compose_commands_are_the_stack_starters():
    assert COMPOSE_COMMANDS == {"up", "restart", "compose"}


def test_exports_everything_the_stack_reads_into_the_given_env(resolvers):
    env = {}
    exported = export_compose_environment(vaulted_settings(), env)

    assert set(DATABASE_VARIABLES) <= set(env)
    assert env["POSTGRES_PASSWORD"] == "local-pw"
    assert env["MACROSTRAT_DB_PORT"] == "5433"
    assert env["ELEVATION_DATABASE_URL"] == ELEVATION
    assert env["SECRET_KEY"] == "signing-key"
    assert env["STORAGE_ACCESS_KEY"] == "ak"
    assert env["STORAGE_SECRET_KEY"] == "s3-secret"
    assert len(exported) == 4


def test_exported_urls_carry_no_cli_attribution(resolvers):
    env = {}
    export_compose_environment(vaulted_settings(), env)
    assert "application_name" not in env["MACROSTRAT_DATABASE_URL"]
    assert "application_name" not in env["ELEVATION_DATABASE_URL"]


def test_variables_already_present_are_left_alone(resolvers):
    """The import-time export of a literal config wins; nothing is re-fetched."""
    env = {name: "already" for name in DATABASE_VARIABLES}
    env.update(SECRET_KEY="already", STORAGE_ACCESS_KEY="a", STORAGE_SECRET_KEY="b")
    exported = export_compose_environment(vaulted_settings(), env)
    assert exported == ["ELEVATION_DATABASE_URL"]
    assert env["SECRET_KEY"] == "already"
    assert env["POSTGRES_PASSWORD"] == "already"


def test_one_unresolvable_reference_does_not_stop_the_others(resolvers, caplog):
    env = {}
    exported = export_compose_environment(
        vaulted_settings(databases={"elevation": "broken://elevation"}), env
    )
    assert "ELEVATION_DATABASE_URL" not in env
    assert env["SECRET_KEY"] == "signing-key"
    assert "ELEVATION_DATABASE_URL" not in exported
    assert "Not exporting ELEVATION_DATABASE_URL" in caplog.text
    # The failure names the reference, never a value.
    assert "signing-key" not in caplog.text


def test_absent_sources_are_simply_skipped(resolvers):
    env = {}
    settings = _Settings(database={"host": "h", "password": "p"})
    exported = export_compose_environment(settings, env)
    assert exported == ["the database login"]
    assert "ELEVATION_DATABASE_URL" not in env
    assert "SECRET_KEY" not in env
