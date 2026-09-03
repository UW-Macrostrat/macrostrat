"""Secret-reference parsing, deferral, redaction and resolution."""

from pytest import fixture, mark, raises

from macrostrat.core.secrets import (
    REDACTED,
    RESOLVERS,
    Secret,
    SecretResolutionError,
    as_secret,
    forget_all_secrets,
    is_secret_ref,
    is_sensitive_name,
    redact_mapping,
    redact_text,
    redact_url_passwords,
    refuse_non_interactive_reveal,
    register_resolver,
    resolve_env,
    resolve_file,
    resolved_secret_values,
    reveal,
)


@fixture
def stub_resolver():
    """Register a resolver that counts calls, so deferral is observable."""
    calls = []

    def resolve(body):
        calls.append(body)
        return f"secret-for-{body}"

    forget_all_secrets()
    register_resolver("stub", resolve)
    resolve.calls = calls
    try:
        yield resolve
    finally:
        RESOLVERS.pop("stub", None)
        forget_all_secrets()


class TestReferenceDetection:
    @mark.parametrize(
        "value",
        [
            "op://Macrostrat Prod/macrostrat-db/reader/password",
            "env://MACROSTRAT_READER_PASSWORD",
            "file:///run/secrets/db-password",
            "keychain://macrostrat/reader",
        ],
    )
    def test_registered_schemes_are_references(self, value):
        assert is_secret_ref(value)

    @mark.parametrize(
        "value",
        [
            # The property that matters most: a database URL is a URI, but it
            # is not a secret reference and must pass through untouched.
            "postgresql://user:password@localhost:5432/macrostrat",
            "postgres://user:password@localhost:5432/macrostrat",
            "https://macrostrat.org",
            "s3://macrostrat-tiles",
            "really-secure-key",
            "",
        ],
    )
    def test_unregistered_schemes_are_not_references(self, value):
        assert not is_secret_ref(value)

    @mark.parametrize("value", [None, 5432, True, {"a": 1}, ["op://x/y/z"]])
    def test_non_strings_are_not_references(self, value):
        assert not is_secret_ref(value)

    def test_scheme_is_case_insensitive(self):
        assert is_secret_ref("OP://vault/item/field")

    def test_unrecognized_reference_cannot_be_constructed(self):
        with raises(ValueError, match="not a recognized secret reference"):
            Secret("postgresql://user:pass@host/db")


class TestCompatibilityHinge:
    """A literal must keep behaving exactly as it does today."""

    @mark.parametrize(
        "value",
        ["postgresql://user:password@localhost:5432/macrostrat", "plain", 5432, None],
    )
    def test_literals_pass_through_unchanged(self, value):
        assert as_secret(value) is value

    def test_references_become_secrets(self):
        assert isinstance(as_secret("env://SOME_VAR"), Secret)

    def test_reveal_passes_literals_through(self):
        assert reveal("postgresql://u:p@h/db") == "postgresql://u:p@h/db"
        assert reveal(None) is None


class TestDeferral:
    def test_construction_does_not_resolve(self, stub_resolver):
        Secret("stub://thing")
        assert stub_resolver.calls == []

    def test_get_resolves(self, stub_resolver):
        assert Secret("stub://thing").get() == "secret-for-thing"
        assert stub_resolver.calls == ["thing"]

    def test_cached_by_default(self, stub_resolver):
        s = Secret("stub://thing")
        s.get()
        s.get()
        assert len(stub_resolver.calls) == 1
        assert s.is_resolved

    def test_cache_can_be_disabled(self, stub_resolver):
        """`escalate` credentials must re-authorize on every use."""
        s = Secret("stub://thing", cache=False)
        s.get()
        s.get()
        assert len(stub_resolver.calls) == 2
        assert not s.is_resolved

    def test_forget_drops_the_cached_value(self, stub_resolver):
        s = Secret("stub://thing")
        s.get()
        s.forget()
        s.get()
        assert len(stub_resolver.calls) == 2

    def test_truthy_without_resolving(self, stub_resolver):
        assert bool(Secret("stub://thing"))
        assert stub_resolver.calls == []

    def test_hashable_without_resolving(self, stub_resolver):
        s = Secret("stub://thing")
        assert {s: 1}[Secret("stub://thing")] == 1
        assert stub_resolver.calls == []


class TestRedaction:
    """The value must be awkward to disclose by accident."""

    @fixture
    def secret(self, stub_resolver):
        s = Secret("stub://thing")
        s.get()  # resolved, so a leak would be a real one
        return s

    def test_str_is_redacted(self, secret):
        assert str(secret) == REDACTED

    def test_fstring_is_redacted(self, secret):
        assert f"{secret}" == REDACTED
        assert f"{secret:>40}" == REDACTED

    def test_format_is_redacted(self, secret):
        assert "{}".format(secret) == REDACTED
        assert "%s" % secret == REDACTED

    def test_repr_shows_the_reference_not_the_value(self, secret):
        assert "stub://thing" in repr(secret)
        assert "secret-for-thing" not in repr(secret)

    def test_the_value_is_still_reachable_explicitly(self, secret):
        assert secret.get() == "secret-for-thing"
        assert reveal(secret) == "secret-for-thing"


class TestResolvers:
    def test_env_resolver(self, monkeypatch):
        monkeypatch.setenv("MACROSTRAT_TEST_SECRET", "from-env")
        assert resolve_env("MACROSTRAT_TEST_SECRET") == "from-env"

    def test_env_resolver_reports_the_variable_name(self, monkeypatch):
        monkeypatch.delenv("MACROSTRAT_ABSENT", raising=False)
        with raises(SecretResolutionError, match="MACROSTRAT_ABSENT"):
            resolve_env("MACROSTRAT_ABSENT")

    def test_file_resolver_strips_the_trailing_newline(self, tmp_path):
        p = tmp_path / "db-password"
        p.write_text("hunter2\n")
        assert resolve_file(str(p)) == "hunter2"

    def test_file_resolver_reports_a_missing_file(self, tmp_path):
        with raises(SecretResolutionError, match="could not be read"):
            resolve_file(str(tmp_path / "nope"))

    def test_empty_resolution_is_an_error(self):
        """An empty value means a misconfigured item, not a blank password."""
        register_resolver("blank", lambda body: "")
        try:
            with raises(SecretResolutionError, match="empty value"):
                Secret("blank://x").get()
        finally:
            RESOLVERS.pop("blank", None)

    def test_op_resolver_is_registered(self):
        assert "op" in RESOLVERS


class TestInterning:
    """One reference resolves once per process, however many places name it."""

    def test_same_reference_yields_the_same_secret(self, stub_resolver):
        assert as_secret("stub://pw") is as_secret("stub://pw")

    def test_shared_reference_resolves_once(self, stub_resolver):
        """Four databases sharing a reader credential = one backend fetch."""
        for _ in range(4):
            as_secret("stub://reader").get()
        assert stub_resolver.calls == ["reader"]

    def test_different_references_are_distinct(self, stub_resolver):
        assert as_secret("stub://a") is not as_secret("stub://b")

    def test_cacheability_is_part_of_the_identity(self, stub_resolver):
        assert as_secret("stub://pw") is not as_secret("stub://pw", cache=False)

    def test_uncached_secrets_still_refetch(self, stub_resolver):
        s = as_secret("stub://pw", cache=False)
        s.get()
        as_secret("stub://pw", cache=False).get()
        assert len(stub_resolver.calls) == 2

    def test_forget_all_clears_the_table(self, stub_resolver):
        as_secret("stub://pw").get()
        forget_all_secrets()
        as_secret("stub://pw").get()
        assert len(stub_resolver.calls) == 2


class TestRedaction2:
    """Redaction for commands that print configuration."""

    @mark.parametrize(
        "name",
        [
            "PGPASSWORD",
            "POSTGRES_PASSWORD",
            "SECRET_KEY",
            "STORAGE_SECRET_KEY",
            "RADOSGW_ACCESS_KEY",
            "MAPBOX_TOKEN",
            "OAUTH_CLIENT_SECRET",
            "pgpassword",
        ],
    )
    def test_sensitive_names_are_detected(self, name):
        assert is_sensitive_name(name)

    @mark.parametrize(
        "name",
        ["PGHOST", "PGPORT", "PGUSER", "PGDATABASE", "COMPOSE_FILE", "MACROSTRAT_ENV"],
    )
    def test_debugging_variables_are_not_redacted(self, name):
        """Over-redaction is safe, but must not make printenv useless."""
        assert not is_sensitive_name(name)

    def test_mapping_redacts_by_name(self):
        out = redact_mapping({"PGPASSWORD": "hunter2", "PGHOST": "localhost"})
        assert out["PGPASSWORD"] == REDACTED
        assert out["PGHOST"] == "localhost"

    def test_mapping_redacts_by_value(self, stub_resolver):
        """A credential embedded in something innocuously named."""
        pw = as_secret("stub://pw").get()
        out = redact_mapping({"SOME_URL": f"postgresql://u:{pw}@host/db"})
        assert pw not in out["SOME_URL"]
        assert REDACTED in out["SOME_URL"]

    def test_unresolved_secrets_are_not_matched_by_value(self, stub_resolver):
        as_secret("stub://pw")  # never resolved
        assert resolved_secret_values() == set()

    def test_redact_text_leaves_innocent_text_alone(self):
        assert redact_text("postgresql://u@host/db") == "postgresql://u@host/db"

    def test_reveal_is_refused_without_a_tty(self):
        """pytest captures stdio, so this is the non-interactive case."""
        with raises(SecretResolutionError, match="interactive terminal"):
            refuse_non_interactive_reveal("the password")


class TestUrlPasswordRedaction:
    """A password embedded in a URL, in a variable with an innocent name.

    `MACROSTRAT_DATABASE_URL` carries a live password and matches none of the
    sensitive-name patterns, and for a literal config the password never
    passes through Secret — so neither name- nor value-matching catches it.
    """

    def test_database_url_password_is_masked(self):
        out = redact_text(
            "postgresql://macrostrat-admin:my-cool-password@localhost:5432/macrostrat"
        )
        assert "my-cool-password" not in out
        # The useful parts survive.
        assert "macrostrat-admin" in out and "localhost:5432/macrostrat" in out

    def test_mapping_catches_an_innocently_named_url(self):
        out = redact_mapping(
            {"MACROSTRAT_DATABASE_URL": "postgresql://u:pw@host:5432/db"}
        )
        assert "pw" not in out["MACROSTRAT_DATABASE_URL"].replace("REDACTED", "")
        assert REDACTED in out["MACROSTRAT_DATABASE_URL"]

    @mark.parametrize(
        "url",
        [
            "postgresql://u:p@h/db",
            "postgres://user:pass%40word@h:5432/db",
            "https://user:token@api.example.org/v1",
            "mysql+pymysql://root:secret@localhost/macrostrat",
        ],
    )
    def test_various_schemes(self, url):
        assert REDACTED in redact_url_passwords(url)

    @mark.parametrize(
        "text",
        [
            "postgresql://user@host:5432/db",  # no password
            "https://macrostrat.org",
            "postgresql://localhost:5432/macrostrat",
            "not a url at all",
            "",
        ],
    )
    def test_urls_without_a_password_are_untouched(self, text):
        assert redact_url_passwords(text) == text

    def test_multiple_urls_in_one_value(self):
        out = redact_url_passwords("a=postgres://u:p1@h/db b=https://v:p2@x/y")
        assert "p1" not in out and "p2" not in out
        assert out.count(REDACTED) == 2

    def test_port_is_not_mistaken_for_a_password(self):
        """`host:5432` after an @ must not be masked."""
        out = redact_url_passwords("postgresql://user@host:5432/db")
        assert "5432" in out and REDACTED not in out
