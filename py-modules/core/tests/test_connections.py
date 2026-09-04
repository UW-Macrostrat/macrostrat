"""Composing database connections from topology plus a named credential."""

from pytest import fixture, raises

from macrostrat.core.connections import (
    DatabaseConnection,
    DatabaseRole,
    MissingCredential,
    connection_for,
    connections_for,
    merge_tables,
)
from macrostrat.core.secrets import (
    RESOLVERS,
    Secret,
    forget_all_secrets,
    register_resolver,
)

LEGACY = "postgresql://macrostrat-admin:my-cool-password@localhost:5432/macrostrat"


@fixture
def stub_resolver():
    def resolve(body):
        return f"resolved-{body}"

    forget_all_secrets()
    register_resolver("stub", resolve)
    try:
        yield
    finally:
        RESOLVERS.pop("stub", None)
        forget_all_secrets()


class _Settings(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def dsn(url):
    return url.render_as_string(hide_password=False)


def bare_dsn(url):
    """The DSN without the attributing `application_name`.

    Every composed URL carries one (see TestApplicationName), so tests that
    care about the *configured* parts strip it rather than asserting around it.
    """
    from sqlalchemy.engine import make_url

    query = {k: v for k, v in url.query.items() if k != "application_name"}
    return make_url(url.set(query=query)).render_as_string(hide_password=False)


class TestStructuredTable:
    def test_composes_a_url_per_role(self, stub_resolver):
        c = DatabaseConnection.parse(
            {
                "host": "db.production.svc.macrostrat.org",
                "database": "macrostrat",
                "user": "macrostrat",
                "reader": "stub://reader-pw",
                "writer": "stub://writer-pw",
            }
        )
        assert bare_dsn(c.url(DatabaseRole.Reader)).endswith(
            "@db.production.svc.macrostrat.org:5432/macrostrat"
        )
        assert "resolved-reader-pw" in dsn(c.url(DatabaseRole.Reader))
        assert "resolved-writer-pw" in dsn(c.url(DatabaseRole.Writer))

    def test_references_are_not_resolved_at_parse_time(self):
        """Parsing config must not reach for a password manager."""
        c = DatabaseConnection.parse(
            {"host": "h", "database": "d", "reader": "op://v/i/reader/password"}
        )
        assert isinstance(c.reader, Secret)
        assert not c.reader.is_resolved

    def test_literal_password_stays_a_plain_string(self):
        c = DatabaseConnection.parse(
            {"host": "h", "database": "d", "password": "hunter2"}
        )
        assert c.reader == "hunter2"
        assert not isinstance(c.reader, Secret)

    def test_shared_password_serves_both_roles(self):
        c = DatabaseConnection.parse(
            {"host": "h", "database": "d", "password": "hunter2"}
        )
        assert "hunter2" in dsn(c.url(DatabaseRole.Reader))
        assert "hunter2" in dsn(c.url(DatabaseRole.Writer))

    def test_per_role_credential_overrides_the_shared_one(self, stub_resolver):
        c = DatabaseConnection.parse(
            {
                "host": "h",
                "database": "d",
                "password": "shared",
                "writer": "stub://only-writer",
            }
        )
        assert "shared" in dsn(c.url(DatabaseRole.Reader))
        assert "resolved-only-writer" in dsn(c.url(DatabaseRole.Writer))

    def test_per_role_user(self):
        c = DatabaseConnection.parse(
            {
                "host": "h",
                "database": "d",
                "password": "p",
                "reader_user": "macrostrat_reader",
                "writer_user": "macrostrat-admin",
            }
        )
        assert c.url(DatabaseRole.Reader).username == "macrostrat_reader"
        assert c.url(DatabaseRole.Writer).username == "macrostrat-admin"

    def test_missing_role_names_the_role_and_not_a_secret(self):
        c = DatabaseConnection.parse(
            {"host": "h", "database": "d", "writer": "literal-pw"}
        )
        with raises(MissingCredential) as err:
            c.url(DatabaseRole.Reader)
        assert "reader" in str(err.value)
        assert "literal-pw" not in str(err.value)

    def test_host_and_database_are_required(self):
        with raises(ValueError, match="host` and `database"):
            DatabaseConnection.parse({"host": "h"})

    def test_awkward_password_is_quoted_correctly(self):
        """A hand-written URL gets this wrong silently; URL.create doesn't."""
        c = DatabaseConnection.parse(
            {"host": "h", "database": "d", "password": "p@ss/w:rd?#"}
        )
        url = c.url(DatabaseRole.Reader)
        assert url.password == "p@ss/w:rd?#"
        # And it round-trips through the rendered DSN.
        from sqlalchemy.engine import make_url

        assert make_url(dsn(url)).password == "p@ss/w:rd?#"


class TestPasswordDisclosure:
    def test_str_of_a_url_masks_the_password(self):
        c = DatabaseConnection.parse(
            {"host": "h", "database": "d", "password": "hunter2"}
        )
        assert "hunter2" not in str(c.url(DatabaseRole.Reader))

    def test_repr_of_the_connection_does_not_carry_a_resolved_secret(
        self, stub_resolver
    ):
        c = DatabaseConnection.parse(
            {"host": "h", "database": "d", "reader": "stub://pw"}
        )
        c.url(DatabaseRole.Reader)  # resolve and cache
        assert "resolved-pw" not in repr(c)


class TestLegacyCompatibility:
    """The property that lets this land: existing configs are unaffected."""

    def test_legacy_url_still_resolves(self):
        conn = connection_for(_Settings(pg_database=LEGACY))
        assert conn.host == "localhost"
        assert conn.database == "macrostrat"
        assert conn.user == "macrostrat-admin"
        assert bare_dsn(conn.url(DatabaseRole.Writer)) == LEGACY

    def test_legacy_url_credential_serves_both_roles(self):
        """One admin login used for everything — today's actual behaviour."""
        conn = connection_for(_Settings(pg_database=LEGACY))
        reader, writer = conn.url(DatabaseRole.Reader), conn.url(DatabaseRole.Writer)
        # The URLs now differ by `application_name`, which names the role;
        # what must be identical is the credential.
        assert reader.password == writer.password
        assert reader.username == writer.username
        assert bare_dsn(reader) == bare_dsn(writer)

    def test_structured_table_wins_when_present(self):
        conn = connection_for(
            _Settings(
                pg_database=LEGACY,
                database={"host": "new-host", "database": "d", "password": "p"},
            )
        )
        assert conn.host == "new-host"

    def test_unusable_table_falls_back_to_the_legacy_key(self):
        """A malformed new-style table must not take an environment offline."""
        conn = connection_for(
            _Settings(pg_database=LEGACY, database={"host": "only-a-host"})
        )
        assert conn.host == "localhost"

    def test_whole_url_may_itself_be_a_secret_reference(self, stub_resolver):
        """The smallest adoption step: no structural change at all."""
        register_resolver("wholeurl", lambda body: LEGACY)
        try:
            conn = connection_for(_Settings(pg_database="wholeurl://macrostrat"))
            assert conn.host == "localhost"
            assert bare_dsn(conn.url(DatabaseRole.Writer)) == LEGACY
        finally:
            RESOLVERS.pop("wholeurl", None)

    def test_no_database_configured_is_none_not_an_error(self):
        assert connection_for(_Settings()) is None
        # config.py's long-standing "None"-as-a-string quirk.
        assert connection_for(_Settings(pg_database="None")) is None


class TestConnectionOptions:
    """Decomposing a URL and rebuilding it must not drop its parameters.

    `sslmode` is the one that matters: silently losing it downgrades a
    required-TLS connection to whatever the server will accept.
    """

    SSL = (
        "postgresql://admin:pw@db.example.org:5432/macrostrat"
        "?sslmode=require&connect_timeout=10"
    )

    def test_legacy_url_query_params_round_trip(self):
        from sqlalchemy.engine import make_url

        c = DatabaseConnection.from_url(self.SSL)
        assert c.options == {"sslmode": "require", "connect_timeout": "10"}
        # SQLAlchemy orders query keys canonically, so compare the parsed URLs
        # rather than the rendered strings.
        assert make_url(bare_dsn(c.url(DatabaseRole.Writer))) == make_url(self.SSL)

    def test_options_table_is_carried_into_the_url(self):
        c = DatabaseConnection.parse(
            {
                "host": "h",
                "database": "d",
                "password": "p",
                "options": {"sslmode": "verify-full"},
            }
        )
        assert "sslmode=verify-full" in dsn(c.url(DatabaseRole.Reader))

    def test_options_apply_to_both_roles(self):
        c = DatabaseConnection.parse(
            {
                "host": "h",
                "database": "d",
                "password": "p",
                "options": {"sslmode": "require"},
            }
        )
        for role in DatabaseRole:
            assert "sslmode=require" in dsn(c.url(role))

    def test_no_options_yields_no_configured_query_params(self):
        c = DatabaseConnection.parse({"host": "h", "database": "d", "password": "p"})
        assert "?" not in bare_dsn(c.url(DatabaseRole.Reader))

    def test_malformed_options_table_is_rejected(self):
        with raises(ValueError, match="options"):
            DatabaseConnection.parse(
                {"host": "h", "database": "d", "options": "sslmode=require"}
            )


class TestNamedDatabases:
    """Several databases per environment, without restating the server."""

    BASE = {
        "host": "db.production.svc.macrostrat.org",
        "database": "macrostrat",
        "password": "pw",
        "options": {"sslmode": "require"},
    }

    def test_bare_name_inherits_the_default_server(self):
        conns = connections_for(
            _Settings(database=self.BASE, databases={"rockd": "rockd", "sgp": "sgp"})
        )
        assert set(conns) == {"macrostrat", "rockd", "sgp"}
        rockd = conns["rockd"]
        assert rockd.host == "db.production.svc.macrostrat.org"
        assert rockd.database == "rockd"
        # Credentials and options come along too — that's the whole point.
        assert "pw" in dsn(rockd.url(DatabaseRole.Reader))
        assert "sslmode=require" in dsn(rockd.url(DatabaseRole.Reader))

    def test_table_states_only_its_differences(self):
        conns = connections_for(
            _Settings(
                database=self.BASE,
                databases={
                    "elevation": {"host": "elev.example.org", "database": "elevation"}
                },
            )
        )
        elev = conns["elevation"]
        assert elev.host == "elev.example.org"
        assert elev.database == "elevation"
        # Inherited from the default table.
        assert "sslmode=require" in dsn(elev.url(DatabaseRole.Reader))

    def test_named_url_entries_still_work(self):
        """This key already holds URLs today; those must keep resolving."""
        conns = connections_for(
            _Settings(database=self.BASE, databases={"burwell": LEGACY})
        )
        assert conns["burwell"].host == "localhost"
        assert conns["burwell"].database == "macrostrat"

    def test_named_secret_ref_resolves_to_a_url(self, stub_resolver):
        register_resolver("wholeurl", lambda body: LEGACY)
        try:
            conns = connections_for(
                _Settings(database=self.BASE, databases={"b": "wholeurl://x"})
            )
            assert conns["b"].host == "localhost"
        finally:
            RESOLVERS.pop("wholeurl", None)

    def test_per_database_credential_override(self, stub_resolver):
        conns = connections_for(
            _Settings(
                database=self.BASE,
                databases={"sgp": {"database": "sgp", "writer": "stub://sgp-pw"}},
            )
        )
        assert "resolved-sgp-pw" in dsn(conns["sgp"].url(DatabaseRole.Writer))
        # The inherited shared password still serves the reader.
        assert "pw" in dsn(conns["sgp"].url(DatabaseRole.Reader))

    def test_explicit_default_table_outranks_the_injected_legacy_url(self):
        """config.py injects databases['macrostrat'] from pg_database."""
        conns = connections_for(
            _Settings(database=self.BASE, databases={"macrostrat": LEGACY})
        )
        assert conns["macrostrat"].host == "db.production.svc.macrostrat.org"

    def test_bare_name_without_a_default_table_is_skipped_not_fatal(self):
        conns = connections_for(_Settings(pg_database=LEGACY, databases={"x": "x"}))
        assert "x" not in conns
        # The default database still resolves.
        assert conns["macrostrat"].host == "localhost"

    def test_unusable_entries_are_skipped_individually(self):
        conns = connections_for(
            _Settings(database=self.BASE, databases={"good": "good", "bad": 7, "": ""})
        )
        assert "good" in conns and "bad" not in conns

    def test_connection_for_takes_a_name(self):
        s = _Settings(database=self.BASE, databases={"rockd": "rockd"})
        assert connection_for(s, "rockd").database == "rockd"
        assert connection_for(s).database == "macrostrat"
        assert connection_for(s, "absent") is None


class TestDefaultLayerInheritance:
    """`[default.database]` is written once, not once per tier."""

    class _WithDefault(_Settings):
        def __init__(self, default_table, **values):
            super().__init__(**values)
            self._default = default_table

        def from_env(self, name):
            return _Settings(database=self._default)

    def test_default_table_is_inherited(self):
        s = self._WithDefault(
            {"port": 5433, "password": "shared-pw", "options": {"sslmode": "require"}},
            database={"host": "h", "database": "macrostrat"},
        )
        c = connection_for(s)
        assert c.port == 5433
        assert "shared-pw" in dsn(c.url(DatabaseRole.Reader))
        assert "sslmode=require" in dsn(c.url(DatabaseRole.Reader))

    def test_environment_overrides_the_default(self):
        s = self._WithDefault(
            {"port": 5433, "password": "shared"},
            database={"host": "h", "database": "d", "port": 6000},
        )
        assert connection_for(s).port == 6000

    def test_options_merge_rather_than_replace(self):
        s = self._WithDefault(
            {"options": {"sslmode": "require", "connect_timeout": "10"}},
            database={
                "host": "h",
                "database": "d",
                "password": "p",
                "options": {"sslmode": "verify-full"},
            },
        )
        c = connection_for(s)
        assert c.options == {"sslmode": "verify-full", "connect_timeout": "10"}

    def test_named_databases_inherit_through_the_default_layer(self):
        s = self._WithDefault(
            {"password": "shared", "options": {"sslmode": "require"}},
            database={"host": "h", "database": "macrostrat"},
            databases={"rockd": "rockd"},
        )
        rockd = connection_for(s, "rockd")
        assert rockd.host == "h" and rockd.database == "rockd"
        assert "sslmode=require" in dsn(rockd.url(DatabaseRole.Reader))


class TestApplicationName:
    """Every connection identifies who, where, and at what privilege.

    pgaudit and pg_stat_activity record `application_name`, so this is what
    makes a logged write attributable to a person, an environment and a role
    rather than to "some client of the admin login".
    """

    def conn(self):
        return DatabaseConnection.parse({"host": "h", "database": "d", "password": "p"})

    def app_name(self, url):
        return url.query["application_name"]

    def test_set_on_every_connection(self, monkeypatch):
        monkeypatch.setenv("USER", "dquinn")
        monkeypatch.setenv("MACROSTRAT_ENV", "production")
        assert (
            self.app_name(self.conn().url(DatabaseRole.Writer))
            == "macrostrat-cli/dquinn@production/writer"
        )

    def test_names_the_role(self, monkeypatch):
        monkeypatch.setenv("USER", "dquinn")
        monkeypatch.setenv("MACROSTRAT_ENV", "production")
        c = self.conn()
        assert self.app_name(c.url(DatabaseRole.Reader)).endswith("/reader")
        assert self.app_name(c.url(DatabaseRole.Writer)).endswith("/writer")

    def test_survives_url_round_trip_unencoded(self, monkeypatch):
        """`/` and `@` are percent-encoded in the URL string only.

        What reaches Postgres — and so pg_stat_activity — is the clean value.
        """
        from sqlalchemy.engine import make_url

        monkeypatch.setenv("USER", "dquinn")
        monkeypatch.setenv("MACROSTRAT_ENV", "staging")
        rendered = dsn(self.conn().url(DatabaseRole.Writer))
        assert "%2F" in rendered  # encoded in transit
        assert (
            make_url(rendered).query["application_name"]
            == "macrostrat-cli/dquinn@staging/writer"
        )

    def test_fits_the_postgres_63_byte_limit(self, monkeypatch):
        """Postgres truncates silently past NAMEDATALEN-1; do it deliberately."""
        monkeypatch.setenv("USER", "a" * 200)
        monkeypatch.setenv("MACROSTRAT_ENV", "production")
        name = self.app_name(self.conn().url(DatabaseRole.Writer))
        assert len(name) <= 63
        # The role is the security-relevant part and must not be what is lost.
        assert name.endswith("@production/writer")

    def test_an_explicit_application_name_is_respected(self):
        c = DatabaseConnection.parse(
            {
                "host": "h",
                "database": "d",
                "password": "p",
                "options": {"application_name": "map-ingest-worker"},
            }
        )
        assert self.app_name(c.url(DatabaseRole.Writer)) == "map-ingest-worker"

    def test_missing_user_and_env_do_not_raise(self, monkeypatch):
        monkeypatch.delenv("USER", raising=False)
        monkeypatch.delenv("USERNAME", raising=False)
        monkeypatch.delenv("MACROSTRAT_ENV", raising=False)
        assert (
            self.app_name(self.conn().url(DatabaseRole.Reader))
            == "macrostrat-cli/unknown@no-env/reader"
        )
