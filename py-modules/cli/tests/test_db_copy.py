"""`macrostrat db copy` off the cluster: the same arguments, run on this machine."""

from types import SimpleNamespace

from click import ClickException
from pytest import fixture, mark, raises
from sqlalchemy.engine.url import URL

from macrostrat.cli.database import copy as copy_module
from macrostrat.cli.database.copy import LocalCopy, copy_command, describe

SOURCE = URL.create(
    "postgresql+psycopg",
    username="reader",
    password="source-secret",
    host="db.development.example",
    port=5432,
    database="macrostrat",
)
DESTINATION = URL.create(
    "postgresql+psycopg",
    username="admin",
    password="local-secret",
    host="localhost",
    port=54884,
    database="macrostrat",
)


def _spec(**kwargs) -> LocalCopy:
    return LocalCopy(source=SOURCE, destination=DESTINATION, **kwargs)


def test_arguments_match_the_cluster_copy():
    spec = _spec(tables=["maps.sources"], schemas=["macrostrat_kg"], replace=True)
    assert spec.dump_args() == [
        "--format=custom",
        "--verbose",
        "--table",
        "maps.sources",
        "--schema",
        "macrostrat_kg",
    ]
    assert spec.restore_args() == [
        "--verbose",
        "--single-transaction",
        "--clean",
        "--if-exists",
        "--dbname",
        "macrostrat",
    ]


def test_passwords_reach_containers_only_through_their_environment():
    spec = _spec(tables=["maps.sources"], image="postgres:15")
    for (cmd, env), password in (
        (spec.dump(), "source-secret"),
        (spec.restore(), "local-secret"),
    ):
        assert not any(password in arg for arg in cmd)
        assert env["PGPASSWORD"] == password
        # Forwarded by name, so docker reads it from its own environment.
        assert cmd[cmd.index("PGPASSWORD") - 1] == "-e"
        assert "postgres:15" in cmd


def test_dry_run_output_hides_passwords():
    spec = _spec(tables=["maps.sources"])
    shown = describe(spec.dump()) + describe(spec.restore())
    assert "secret" not in shown
    assert "PGHOST=db.development.example" in shown


def test_containers_reach_a_local_database_by_the_configured_name():
    spec = _spec(tables=["maps.sources"], docker_localhost="host.docker.internal")
    _, source_env = spec.dump()
    _, destination_env = spec.restore()
    assert source_env["PGHOST"] == "db.development.example"
    assert destination_env["PGHOST"] == "host.docker.internal"


@fixture
def host():
    calls = []
    return SimpleNamespace(
        active=SimpleNamespace(name="local"),
        calls=calls,
        require_read=lambda env, **k: calls.append(("read", env)),
        require_write=lambda scope, env, **k: calls.append(("write", scope, env)),
    )


def _copy(host, source="development", **kwargs):
    options = dict(
        table=["maps.sources"],
        schema=[],
        database="macrostrat",
        replace=False,
        timeout=6,
        image=None,
        follow=True,
        dry_run=False,
        yes=False,
    )
    options.update(kwargs)
    return copy_command(host)(source, **options)


@mark.parametrize(
    "source, options, message",
    [
        ("local", {}, "same database"),
        ("development", {"table": []}, "at least one --table or --schema"),
        ("development", {"follow": False}, "runs in this terminal"),
    ],
)
def test_refused_before_any_gate_or_credential(host, source, options, message):
    with raises(ClickException, match=message):
        _copy(host, source, **options)
    assert host.calls == []


class _Settings:
    def __init__(self, url):
        self._url = url

    def database_url(self, role):
        return self._url

    def get(self, key, default=None):
        return default


def test_dry_run_reads_but_does_not_ask_to_write(host, monkeypatch, capsys):
    settings = {"development": _Settings(SOURCE), "local": _Settings(DESTINATION)}
    monkeypatch.setattr(
        "macrostrat.core.database._settings_for_env", lambda env: settings[env]
    )
    monkeypatch.setattr(copy_module.asyncio, "run", None)  # nothing may run

    _copy(host, dry_run=True)

    assert host.calls == [("read", "development")]
    out = capsys.readouterr().out
    assert "pg_dump" in out and "pg_restore" in out and "secret" not in out
