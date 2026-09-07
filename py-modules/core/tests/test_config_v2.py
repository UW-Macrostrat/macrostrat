"""The opt-in schema-validated loader, and its Dynaconf-shaped surface."""

from pathlib import Path

from pytest import fixture, mark, raises

from macrostrat.core import secrets
from macrostrat.core.config_loader import (
    CONFIG_VERSION_VAR,
    MacrostratSettings,
    config_version,
    deep_merge,
    environment_overrides,
    load_settings_v2,
    merged_environment,
    validate_environment,
)
from macrostrat.core.config_model import BackendType, EnvironmentSettings
from macrostrat.core.connections import DatabaseRole, DeferredUrlConnection
from macrostrat.core.environment import EnvironmentClass
from macrostrat.core.exc import ConfigError, UnknownEnvironment
from macrostrat.core.secrets import RESOLVERS, forget_all_secrets, register_resolver

CONFIG = """
config_version = 2
mapbox_token = "pk.top-level"

[default]
pg_database_container = "imresamu/postgis:15-3.4"
log_modules = ["macrostrat", "sqlalchemy.engine"]

[default.database]
port = 5432

[default.storage]
endpoint = "https://storage.example.org"

[local]
env_class = "local"
backend = "docker-compose"
compose_root = "./local-root"
token_signing_key = "local-signing-key"
op_account = "work.1password.com"

[local.database]
host = "localhost"
port = 5433
user = "macrostrat-admin"
password = "local-pw"

[local.databases]
rockd = "rockd"
test = "macrostrat_test"
elevation = "stub://elevation-url"
burwell = "postgresql://u:p@legacy:5432/burwell"

[local.storage]
access_key = "ak"
secret_key = "sk"
rockd_backup_access = "legacy-extra"

[local.storage.buckets]
map-staging = "map-datafiles"

[local.storage.admin]
type = "ceph-object-storage"
access_key = "stub://admin-ak"
secret_key = "stub://admin-sk"

[production]
env_class = "production"
database = "stub://prod-url"
token_signing_key = "stub://prod-key"

[production.write_gate]
data = "typed"

[nameless]
base_url = "https://nameless.example.org"
"""

ELEVATION = "postgresql://e:e-pw@db.development.svc:5432/elevation"


@fixture
def stub_resolver():
    calls = []

    def resolve(body):
        calls.append(body)
        return {"elevation-url": ELEVATION}.get(body, f"resolved-{body}")

    forget_all_secrets()
    register_resolver("stub", resolve)
    resolve.calls = calls
    try:
        yield resolve
    finally:
        RESOLVERS.pop("stub", None)
        forget_all_secrets()
        secrets.configure_onepassword(None)


@fixture
def config_file(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "local-root").mkdir()
    cfg = root / "macrostrat.toml"
    cfg.write_text(CONFIG)
    return cfg


class TestLayering:
    def test_deep_merge_recurses_into_tables_and_replaces_lists(self):
        base = {"a": 1, "t": {"x": 1, "y": 1}, "l": [1, 2]}
        out = deep_merge(base, {"t": {"y": 2, "z": 3}, "l": [3]})
        assert out == {"a": 1, "t": {"x": 1, "y": 2, "z": 3}, "l": [3]}
        # The inputs are untouched.
        assert base["t"] == {"x": 1, "y": 1}

    def test_top_level_then_default_then_environment(self):
        raw = {
            "config_version": 2,
            "mapbox_token": "top",
            "default": {"base_url": "https://default", "database": {"port": 1}},
            "prod": {"base_url": "https://prod", "database": {"host": "h"}},
        }
        merged = merged_environment(raw, "prod")
        assert merged["mapbox_token"] == "top"
        assert merged["base_url"] == "https://prod"
        assert merged["database"] == {"port": 1, "host": "h"}
        assert "config_version" not in merged

    def test_no_environment_is_the_default_layer(self):
        raw = {"default": {"base_url": "https://default"}, "prod": {}}
        assert merged_environment(raw, None) == {"base_url": "https://default"}


class TestEnvironmentOverrides:
    def test_prefixed_variables_become_settings(self):
        out = environment_overrides(
            {
                "MACROSTRAT_BASE_URL": "https://override",
                "MACROSTRAT_DATABASE__PORT": "5433",
                "MACROSTRAT_OFFLINE": "true",
                "MACROSTRAT_BACKEND": "docker-compose",
                "HOME": "/nowhere",
            }
        )
        assert out == {
            "base_url": "https://override",
            "database": {"port": 5433},
            "offline": True,
            "backend": "docker-compose",
        }

    @mark.parametrize(
        "name",
        [
            "MACROSTRAT_ENV",
            "MACROSTRAT_ENV_EXPIRES",
            "MACROSTRAT_CONFIG",
            "MACROSTRAT_CONFIG_VERSION",
            "MACROSTRAT_ROOT",
            "MACROSTRAT_PYROOT",
            "MACROSTRAT_DATABASE_URL",
            "MACROSTRAT_DB_PORT",
            "MACROSTRAT_API_SRC",
        ],
    )
    def test_control_variables_are_never_settings(self, name):
        assert environment_overrides({name: "x"}) == {}


class TestValidation:
    def test_removed_keys_are_errors_that_name_the_replacement(self):
        with raises(ConfigError) as info:
            validate_environment(
                {
                    "env_class": "local",
                    "pg_database": "postgresql://x",
                    "secret_key": "k",
                },
                "local",
            )
        text = str(info.value.details)
        assert "pg_database" in text and "[<env>.database]" in text
        assert "secret_key" in text and "token_signing_key" in text

    def test_removed_database_spellings_are_errors(self):
        with raises(ConfigError) as info:
            validate_environment(
                {"env_class": "local", "database": {"host": "h", "reader": "x"}},
                "local",
            )
        assert "read_password" in str(info.value.details)

    def test_env_class_is_required_for_a_named_environment(self):
        with raises(ConfigError) as info:
            validate_environment({"base_url": "https://x"}, "staging")
        assert 'env_class = "staging"' in str(info.value.details)

    def test_env_class_is_not_required_when_no_environment_is_selected(self):
        assert validate_environment({"base_url": "https://x"}, None).env_class is None

    def test_unknown_env_class_is_an_error(self):
        with raises(ConfigError):
            validate_environment({"env_class": "prod-ish"}, "x")

    def test_types_are_enforced(self):
        with raises(ConfigError) as info:
            validate_environment(
                {"env_class": "local", "database": {"host": "h", "port": "lots"}},
                "local",
            )
        assert "database.port" in str(info.value.details)

    def test_unknown_top_level_keys_are_kept_and_reported(self):
        s = validate_environment({"env_class": "local", "editr": "vim"}, "local")
        assert s.unknown_keys() == ["editr"]

    def test_database_may_be_a_url_string(self):
        s = validate_environment(
            {"env_class": "local", "database": "postgresql://u:p@h/d"}, "local"
        )
        assert s.database == "postgresql://u:p@h/d"

    def test_item_sugar_expands_to_login_references(self):
        s = validate_environment(
            {"env_class": "local", "database": {"host": "h", "item": "op://V/i/"}},
            "local",
        )
        assert s.database.user == "op://V/i/username"
        assert s.database.password == "op://V/i/password"

    def test_item_sugar_does_not_override_explicit_fields(self):
        s = validate_environment(
            {
                "env_class": "local",
                "storage": {
                    "endpoint": "e",
                    "item": "op://V/i",
                    "secret_key": "op://V/i/other",
                },
            },
            "local",
        )
        assert s.storage.access_key == "op://V/i/access_key"
        assert s.storage.secret_key == "op://V/i/other"

    def test_the_schema_documents_every_key(self):
        schema = EnvironmentSettings.model_json_schema()
        props = schema["properties"]
        assert "env_class" in props and "database" in props and "storage" in props
        assert props["token_signing_key"]["description"]


class TestVersionDetection:
    def test_default_is_one(self, tmp_path):
        cfg = tmp_path / "macrostrat.toml"
        cfg.write_text('[local]\nenv_class = "local"\n')
        assert config_version(cfg) == 1

    def test_declared_in_the_file(self, config_file):
        assert config_version(config_file) == 2

    def test_declared_in_the_environment(self, tmp_path, monkeypatch):
        cfg = tmp_path / "macrostrat.toml"
        cfg.write_text('[local]\nenv_class = "local"\n')
        monkeypatch.setenv(CONFIG_VERSION_VAR, "2")
        assert config_version(cfg) == 2

    def test_no_file_is_version_one(self, monkeypatch):
        monkeypatch.delenv(CONFIG_VERSION_VAR, raising=False)
        assert config_version(None) == 1


class TestLoadedSettings:
    @fixture
    def settings(self, config_file, stub_resolver, monkeypatch):
        monkeypatch.delenv(CONFIG_VERSION_VAR, raising=False)
        return load_settings_v2(config_file, "local", environ={})

    def test_typed_attributes(self, settings):
        assert isinstance(settings, MacrostratSettings)
        assert settings.env == "local"
        assert settings.env_class == EnvironmentClass.Local
        assert settings.backend == BackendType.DockerCompose
        assert settings.backend == "docker-compose"
        assert isinstance(settings.compose_root, Path)
        assert settings.compose_root.is_absolute()
        assert settings.log_modules == ["macrostrat", "sqlalchemy.engine"]

    def test_top_level_and_default_keys_are_inherited(self, settings):
        assert settings.mapbox_token == "pk.top-level"
        assert settings.pg_database_container == "imresamu/postgis:15-3.4"

    def test_get_returns_plain_values_and_walks_dotted_keys(self, settings):
        assert settings.get("env_class") == "local"
        assert settings.get("storage.endpoint") == "https://storage.example.org"
        assert settings.get("storage.buckets.map-staging") == "map-datafiles"
        assert settings.get("storage.rockd_backup_access") == "legacy-extra"
        assert settings.get("absent", "dflt") == "dflt"
        assert settings.get("storage.absent", "dflt") == "dflt"

    def test_get_results_allow_attribute_access_like_dynaconf(self, settings):
        admin = settings.get("storage.admin")
        assert admin.type == "ceph-object-storage"
        assert admin["type"] == "ceph-object-storage"

    def test_get_is_case_insensitive_on_the_first_segment(self, settings):
        assert settings.get("ROCKD_DATABASE") == settings.rockd_database
        assert "env_class" in settings
        assert settings["env_class"] == "local"

    def test_legacy_url_keys_read_as_composed_urls(self, settings, stub_resolver):
        assert settings.pg_database == (
            "postgresql://macrostrat-admin:local-pw@localhost:5433/macrostrat"
        )
        assert settings.rockd_database.endswith("@localhost:5433/rockd")
        assert settings.get("pg_database") == settings.pg_database
        # A vaulted entry is not composed: that would fetch it.
        assert settings.elevation_database is None
        assert stub_resolver.calls == []

    def test_secret_key_reads_as_the_token_signing_key(self, settings):
        assert settings.secret_key == "local-signing-key"
        assert settings.get("secret_key") == "local-signing-key"
        assert settings.resolve_token_signing_key() == "local-signing-key"

    def test_databases_subscript_yields_urls_for_literals(self, settings):
        assert settings.databases["test"].endswith("@localhost:5433/macrostrat_test")
        assert (
            settings.databases.get("burwell") == "postgresql://u:p@legacy:5432/burwell"
        )
        assert settings.databases.get("absent") is None
        # A reference is handed back as written.
        assert settings.databases["elevation"] == "stub://elevation-url"
        # Iteration sees the raw specs, so the registry is unaffected.
        assert dict(settings.databases)["rockd"] == "rockd"

    def test_registry_inherits_the_default_layer(self, settings):
        rockd = settings.database_connection("rockd")
        assert rockd.host == "localhost"
        assert rockd.port == 5433
        assert isinstance(
            settings.database_connection("elevation"), DeferredUrlConnection
        )
        url = settings.database_url(DatabaseRole.Reader, "elevation")
        assert url.host == "db.development.svc"

    def test_storage_registry(self, settings):
        assert settings.storage_endpoint().endpoint == "https://storage.example.org"
        assert settings.storage_endpoint("admin").is_admin
        assert settings.buckets() == {"map-staging": "map-datafiles"}

    def test_policy_and_op_account_are_applied(self, settings):
        assert settings.policy.env_class == EnvironmentClass.Local
        assert settings.policy.name == "local"
        assert secrets._OP_ACCOUNT == "work.1password.com"

    def test_unset_keys_read_as_absent_like_dynaconf(self, config_file, stub_resolver):
        """`getattr(settings, "storage", {})` must get its default when unset."""
        s = load_settings_v2(config_file, "production", environ={})
        assert getattr(s, "kube_namespace", None) is None
        with raises(AttributeError):
            s.compose_root
        # Runtime fields are legitimately None and stay readable.
        assert s.policy is not None
        no_env = load_settings_v2(None, None, environ={})
        assert getattr(no_env, "storage", {}) == {}
        assert no_env.env is None and no_env.config_file is None

    def test_tables_answer_dict_style_reads(self, settings):
        storage = settings.storage
        assert storage.get("endpoint") == "https://storage.example.org"
        assert storage.get("rockd_backup_access") == "legacy-extra"
        assert storage.get("absent", "dflt") == "dflt"
        assert "buckets" in storage and "region" not in storage
        assert storage["buckets"] == {"map-staging": "map-datafiles"}
        assert getattr(storage, "buckets", {})["map-staging"] == "map-datafiles"

    def test_all_environments_excludes_default(self, settings):
        assert settings.all_environments() == ["local", "production", "nameless"]

    def test_srcroot_is_the_repository_root(self, settings):
        assert (settings.srcroot / "py-modules").is_dir()


class TestLoadFailures:
    def test_unknown_environment_lists_the_available_ones(self, config_file):
        with raises(UnknownEnvironment) as info:
            load_settings_v2(config_file, "staging", environ={})
        assert info.value.available == ["local", "production", "nameless"]

    def test_environment_without_a_class_is_refused(self, config_file):
        with raises(ConfigError) as info:
            load_settings_v2(config_file, "nameless", environ={})
        assert "env_class" in str(info.value.details)

    def test_missing_env_file_is_an_error(self, tmp_path):
        cfg = tmp_path / "macrostrat.toml"
        cfg.write_text(
            'config_version = 2\n[local]\nenv_class = "local"\nenv_files = ["nope.env"]\n'
        )
        with raises(ConfigError) as info:
            load_settings_v2(cfg, "local", environ={})
        assert "nope.env" in str(info.value.message)

    def test_environment_overrides_apply_last(self, config_file, stub_resolver):
        s = load_settings_v2(
            config_file,
            "local",
            environ={
                "MACROSTRAT_BASE_URL": "https://override",
                "MACROSTRAT_DATABASE__PORT": "6000",
            },
        )
        assert s.base_url == "https://override"
        assert s.database_connection().port == 6000

    def test_no_config_file_yields_an_empty_default_layer(self, monkeypatch):
        s = load_settings_v2(None, None, environ={})
        assert s.env is None and s.config_file is None
        assert s.database_connection() is None
        assert s.all_environments() == []


class TestProductionShape:
    def test_a_vaulted_url_default_database_is_deferred(
        self, config_file, stub_resolver
    ):
        s = load_settings_v2(config_file, "production", environ={})
        assert isinstance(s.database_connection(), DeferredUrlConnection)
        assert s.pg_database is None
        assert stub_resolver.calls == []
        assert s.policy.gate_for("data").value == "typed"
        assert s.policy.gate_for("schema").value == "escalate"
