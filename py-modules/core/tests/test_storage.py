"""Storage endpoints: composition, named endpoints, and admin separation."""

import os
import stat
from pathlib import Path

from pytest import fixture, mark, raises

from macrostrat.core.secrets import (
    RESOLVERS,
    Secret,
    forget_all_secrets,
    register_resolver,
)
from macrostrat.core.storage import (
    ADMIN_ENDPOINT,
    DEFAULT_ENDPOINT,
    MissingStorageCredential,
    StorageEndpoint,
    StorageType,
    buckets_for,
    credential_file,
    endpoint_for,
    endpoints_for,
    token_signing_key_value,
)


@fixture
def stub_resolver():
    calls = []

    def resolve(body):
        calls.append(body)
        return f"resolved-{body}"

    forget_all_secrets()
    register_resolver("stub", resolve)
    resolve.calls = calls
    try:
        yield resolve
    finally:
        RESOLVERS.pop("stub", None)
        forget_all_secrets()


class _Settings(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _WithDefault(_Settings):
    def __init__(self, default_storage, **values):
        super().__init__(**values)
        self._default = default_storage

    def from_env(self, name):
        return _Settings(storage=self._default)


BASE = {
    "endpoint": "https://storage.macrostrat.org",
    "access_key": "AKIA-literal",
    "secret_key": "shh-literal",
}


class TestEndpointComposition:
    def test_credentials_resolve_on_demand(self, stub_resolver):
        e = StorageEndpoint.parse(
            {
                "endpoint": "https://storage.macrostrat.org",
                "access_key": "stub://ak",
                "secret_key": "stub://sk",
            }
        )
        assert isinstance(e.access_key, Secret)
        assert stub_resolver.calls == []
        assert e.credentials() == ("resolved-ak", "resolved-sk")

    def test_literal_credentials_stay_plain(self):
        e = StorageEndpoint.parse(BASE)
        assert e.credentials() == ("AKIA-literal", "shh-literal")

    def test_missing_credential_names_the_field(self):
        e = StorageEndpoint.parse({"endpoint": "https://s.example.org"})
        with raises(MissingStorageCredential) as err:
            e.credentials()
        assert "access_key" in str(err.value) and "secret_key" in str(err.value)

    def test_endpoint_is_required(self):
        with raises(ValueError, match="endpoint"):
            StorageEndpoint.parse({"access_key": "a", "secret_key": "b"})

    @mark.parametrize(
        "endpoint,host,secure",
        [
            ("https://storage.macrostrat.org", "storage.macrostrat.org", True),
            ("http://localhost:9000", "localhost:9000", False),
            ("storage.macrostrat.org", "storage.macrostrat.org", None),
        ],
    )
    def test_host_and_scheme_are_derived(self, endpoint, host, secure):
        e = StorageEndpoint.parse({"endpoint": endpoint})
        assert e.host == host
        assert e.secure is secure

    def test_unknown_scheme_yields_none_not_a_guess(self):
        """Guessing here is how a client talks plaintext to a TLS endpoint."""
        assert StorageEndpoint.parse({"endpoint": "s.example.org"}).secure is None


class TestAdminSeparation:
    ADMIN = {
        "type": "ceph-object-storage",
        "access_key": "stub://admin-ak",
        "secret_key": "stub://admin-sk",
    }

    def test_admin_is_a_separate_named_endpoint(self, stub_resolver):
        eps = endpoints_for(_Settings(storage={**BASE, "admin": self.ADMIN}))
        assert set(eps) == {DEFAULT_ENDPOINT, ADMIN_ENDPOINT}
        assert eps[ADMIN_ENDPOINT].is_admin
        assert not eps[DEFAULT_ENDPOINT].is_admin

    def test_resolving_the_default_does_not_resolve_admin(self, stub_resolver):
        """Nothing should reach a cluster-admin key by accident."""
        eps = endpoints_for(_Settings(storage={**BASE, "admin": self.ADMIN}))
        eps[DEFAULT_ENDPOINT].credentials()
        assert stub_resolver.calls == []

    def test_admin_inherits_the_endpoint_url(self, stub_resolver):
        eps = endpoints_for(_Settings(storage={**BASE, "admin": self.ADMIN}))
        assert eps[ADMIN_ENDPOINT].endpoint == BASE["endpoint"]
        assert eps[ADMIN_ENDPOINT].credentials() == (
            "resolved-admin-ak",
            "resolved-admin-sk",
        )

    def test_unknown_type_does_not_become_admin(self):
        """A typo must not silently confer cluster administration."""
        eps = endpoints_for(
            _Settings(storage={**BASE, "admin": {"type": "ceph-obj-storage"}})
        )
        assert eps[ADMIN_ENDPOINT].type == StorageType.S3
        assert not eps[ADMIN_ENDPOINT].is_admin


class TestNamedEndpoints:
    def test_bare_string_is_a_bucket_on_the_default_endpoint(self):
        eps = endpoints_for(
            _Settings(storage={**BASE, "endpoints": {"access-logs": "macrostrat-logs"}})
        )
        logs = eps["access-logs"]
        assert logs.endpoint == BASE["endpoint"]
        assert logs.bucket == "macrostrat-logs"
        assert logs.credentials() == ("AKIA-literal", "shh-literal")

    def test_table_states_only_differences(self, stub_resolver):
        eps = endpoints_for(
            _Settings(
                storage={
                    **BASE,
                    "endpoints": {
                        "rockd-backup": {
                            "bucket": "rockd-photo-backup",
                            "access_key": "stub://rb-ak",
                            "secret_key": "stub://rb-sk",
                        }
                    },
                }
            )
        )
        rb = eps["rockd-backup"]
        assert rb.endpoint == BASE["endpoint"]  # inherited
        assert rb.credentials() == ("resolved-rb-ak", "resolved-rb-sk")

    def test_buckets_table_is_not_an_endpoint(self):
        """`buckets` is a name mapping and must not be read as a credential set."""
        eps = endpoints_for(
            _Settings(storage={**BASE, "buckets": {"map-staging": "map-staging-prod"}})
        )
        assert set(eps) == {DEFAULT_ENDPOINT}

    def test_buckets_are_read_separately(self):
        s = _Settings(storage={**BASE, "buckets": {"map-staging": "map-staging-prod"}})
        assert buckets_for(s) == {"map-staging": "map-staging-prod"}

    def test_reserved_names_are_refused(self):
        """`endpoints.admin` must not be able to shadow the admin endpoint."""
        eps = endpoints_for(
            _Settings(storage={**BASE, "endpoints": {"admin": "sneaky", "ok": "b"}})
        )
        assert ADMIN_ENDPOINT not in eps
        assert eps["ok"].bucket == "b"

    def test_reserved_name_cannot_displace_a_real_admin_endpoint(self):
        eps = endpoints_for(
            _Settings(
                storage={
                    **BASE,
                    "admin": {
                        "type": "ceph-object-storage",
                        "access_key": "real",
                        "secret_key": "real",
                    },
                    "endpoints": {"admin": "sneaky"},
                }
            )
        )
        assert eps[ADMIN_ENDPOINT].is_admin
        assert eps[ADMIN_ENDPOINT].bucket is None
        assert eps[ADMIN_ENDPOINT].credentials() == ("real", "real")

    def test_bare_secret_ref_is_refused(self, stub_resolver):
        """A ref where a bucket belongs is a config error, not a bucket name."""
        eps = endpoints_for(
            _Settings(storage={**BASE, "endpoints": {"x": "stub://oops"}})
        )
        assert "x" not in eps

    def test_bad_entries_are_skipped_individually(self):
        eps = endpoints_for(
            _Settings(storage={**BASE, "endpoints": {"good": "b", "bad": 7}})
        )
        assert "good" in eps and "bad" not in eps

    def test_no_storage_configured(self):
        assert endpoints_for(_Settings()) == {}
        assert endpoint_for(_Settings()) is None


class TestDefaultLayerInheritance:
    def test_endpoint_url_written_once(self):
        s = _WithDefault(
            {"endpoint": "https://storage.macrostrat.org"},
            storage={"access_key": "a", "secret_key": "b"},
        )
        assert endpoint_for(s).endpoint == "https://storage.macrostrat.org"

    def test_named_endpoints_inherit_through_the_default_layer(self):
        s = _WithDefault(
            {"endpoint": "https://storage.macrostrat.org"},
            storage={
                "access_key": "a",
                "secret_key": "b",
                "endpoints": {"logs": "macrostrat-logs"},
            },
        )
        logs = endpoint_for(s, "logs")
        assert logs.endpoint == "https://storage.macrostrat.org"
        assert logs.bucket == "macrostrat-logs"


class TestCredentialFile:
    """Some tools only take credentials from a file; keep that window small."""

    def test_contents_are_readable_inside_the_block(self):
        with credential_file("secret-config") as name:
            assert Path(name).read_text() == "secret-config"

    def test_mode_is_0600(self):
        """Never briefly world-readable, as a `>` redirect would be."""
        with credential_file("x") as name:
            assert stat.S_IMODE(os.stat(name).st_mode) == 0o600

    def test_removed_afterwards(self):
        with credential_file("x") as name:
            pass
        assert not Path(name).exists()

    def test_removed_even_on_exception(self):
        with raises(RuntimeError):
            with credential_file("x") as name:
                captured = name
                raise RuntimeError("transfer failed")
        assert not Path(captured).exists()

    def test_truncated_before_unlink(self):
        """A bind mount holds the inode open past the unlink."""
        with credential_file("super-secret") as name:
            fh = open(name, "r")  # stand in for a container's open handle
        try:
            fh.seek(0)
            assert fh.read() == ""
        finally:
            fh.close()

    def test_prefix_and_suffix_are_honoured(self):
        with credential_file("x", prefix="macrostrat-rclone-", suffix=".conf") as name:
            base = Path(name).name
            assert base.startswith("macrostrat-rclone-") and base.endswith(".conf")

    def test_a_missing_file_does_not_raise_on_cleanup(self):
        with credential_file("x") as name:
            Path(name).unlink()  # something else removed it first


class TestTokenSigningKey:
    """The most privileged value in the config, and its confusing name."""

    def test_preferred_name_wins(self):
        s = _Settings()
        s.token_signing_key = "new"
        s.secret_key = "old"
        assert token_signing_key_value(s) == "new"

    def test_legacy_name_still_honoured(self):
        s = _Settings()
        s.secret_key = "old"
        assert token_signing_key_value(s) == "old"

    def test_absent_is_none(self):
        assert token_signing_key_value(_Settings()) is None

    def test_it_is_not_the_storage_secret_key(self):
        """`[<env>.storage].secret_key` must not be read as the signing key."""
        s = _Settings(storage={**BASE, "secret_key": "an-s3-secret"})
        assert token_signing_key_value(s) is None

    def test_a_settings_method_does_not_shadow_the_key(self):
        """Dynaconf resolves keys by attribute access, so a same-named method
        on the settings class would otherwise be returned as the value."""

        class _WithMethod(_Settings):
            def token_signing_key(self):  # the collision
                return "a bound method"

        s = _WithMethod()
        s.secret_key = "the-real-key"
        assert token_signing_key_value(s) == "the-real-key"
