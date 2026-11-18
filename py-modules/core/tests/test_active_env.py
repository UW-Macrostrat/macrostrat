"""Macrostrat's adapters over the remembered environment.

The mechanism itself is tested in `macrostrat.app_frame`.
"""

import os
from datetime import datetime, timedelta, timezone

from pytest import fixture, mark, raises

from macrostrat.app_frame.environments import (
    DEFAULT_TTL,
    EnvironmentClass,
    InvalidDuration,
    format_duration,
    parse_duration,
)
from macrostrat.core import utils
from macrostrat.core.environment import declared_policy_for
from macrostrat.core.utils import (
    ENV_VAR,
    active_environment,
    normalize_macrostrat_env,
    set_active_env,
)

CONFIG = """
[local]
env_class = "local"

[development]
env_class = "development"

[production]
env_class = "production"
"""

TTL = timedelta(minutes=15)


@fixture
def config(tmp_path, monkeypatch):
    """A config file with three environments, found by the utils module."""
    cfg = tmp_path / "project" / "macrostrat.toml"
    cfg.parent.mkdir()
    cfg.write_text(CONFIG)
    monkeypatch.setattr(utils, "find_macrostrat_config", lambda: cfg)
    return cfg


@fixture
def app_state(tmp_path, monkeypatch, config):
    """Isolate app-state.toml, and clear the environment variables."""
    state = tmp_path / "app-state.toml"
    monkeypatch.setattr(utils, "get_app_state_file", lambda: state)
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.delenv(utils.ENV_EXPIRES_VAR, raising=False)
    utils.environment_state.active = None
    yield state
    utils.environment_state.active = None


class TestMacrostratWrappers:
    """What Macrostrat adds to the library's remembered environment."""

    def test_a_remembered_environment_is_exported_for_dynaconf(
        self, app_state, config, monkeypatch
    ):
        set_active_env("development", expires_in=TTL, config_file=config)
        monkeypatch.delenv(ENV_VAR, raising=False)
        assert normalize_macrostrat_env() == "development"
        assert os.environ[ENV_VAR] == "development"
        assert active_environment().source == "remembered"

    def test_the_config_file_is_found_when_not_given(self, app_state, config):
        set_active_env("local", config_file=config)
        assert normalize_macrostrat_env() == "local"

    def test_switching_environment_clears_other_app_state(self, app_state, config):
        utils.set_app_state("active_map", "grand-canyon")
        set_active_env("development", expires_in=TTL, config_file=config)
        assert utils.get_app_state("active_map") is None

    def test_the_pointer_stays_in_app_state(self, app_state, config):
        set_active_env("development", expires_in=TTL, config_file=config)
        assert utils.get_app_state("active_env") == "development"
        assert utils.get_app_state("active_env_config") == str(config.resolve())


class TestDeclaredPolicyForRawToml:
    """Reading the class straight from the file, before settings exist."""

    def write(self, tmp_path, body):
        cfg = tmp_path / "macrostrat.toml"
        cfg.write_text(body)
        return cfg

    def test_reads_a_declared_class(self, tmp_path):
        cfg = self.write(tmp_path, '[production]\nenv_class = "production"\n')
        p = declared_policy_for(cfg, "production")
        assert p.env_class == EnvironmentClass.Production
        assert not p.inferred

    def test_local_by_name(self, tmp_path):
        cfg = self.write(tmp_path, "[local]\npg_database = 'x'\n")
        assert declared_policy_for(cfg, "local").is_local

    def test_undeclared_fails_closed(self, tmp_path):
        cfg = self.write(tmp_path, "[criticalmaas]\npg_database = 'x'\n")
        p = declared_policy_for(cfg, "criticalmaas")
        assert p.env_class == EnvironmentClass.Production
        assert p.inferred

    def test_agrees_with_the_loaded_settings_path(self, tmp_path):
        """It must not be possible for the two readers to disagree."""
        from macrostrat.app_frame.environments import EnvironmentPolicy

        cfg = self.write(
            tmp_path,
            '[staging]\nenv_class = "staging"\n\n[staging.write_gate]\ndata = "escalate"\n',
        )
        raw = declared_policy_for(cfg, "staging")
        loaded = EnvironmentPolicy.resolve(
            "staging", env_class="staging", write_gate={"data": "escalate"}
        )
        assert raw == loaded

    @mark.parametrize("missing", ["/nonexistent/macrostrat.toml", None])
    def test_unreadable_config_fails_closed(self, missing):
        p = declared_policy_for(missing, "staging")
        assert p.env_class == EnvironmentClass.Production

    def test_absent_environment_fails_closed(self, tmp_path):
        cfg = self.write(tmp_path, '[local]\nenv_class = "local"\n')
        p = declared_policy_for(cfg, "nonexistent")
        assert p.env_class == EnvironmentClass.Production

    def test_a_non_table_section_does_not_raise(self, tmp_path):
        cfg = self.write(tmp_path, 'staging = "not-a-table"\n')
        assert declared_policy_for(cfg, "staging").inferred

    @mark.parametrize(
        "klass",
        [c for c in EnvironmentClass],
    )
    def test_class_default_ttl(self, tmp_path, klass):
        cfg = self.write(tmp_path, f'[x]\nenv_class = "{klass.value}"\n')
        assert declared_policy_for(cfg, "x").ttl == DEFAULT_TTL[klass]

    def test_declared_ttl_overrides_the_class_default(self, tmp_path):
        cfg = self.write(
            tmp_path, '[staging]\nenv_class = "staging"\nactive_ttl = "2h"\n'
        )
        assert declared_policy_for(cfg, "staging").ttl == timedelta(hours=2)

    def test_never_means_no_expiry(self, tmp_path):
        cfg = self.write(
            tmp_path, '[development]\nenv_class = "development"\nactive_ttl = "never"\n'
        )
        assert declared_policy_for(cfg, "development").ttl is None

    def test_junk_ttl_falls_back_to_the_class_default(self, tmp_path):
        cfg = self.write(
            tmp_path, '[production]\nenv_class = "production"\nactive_ttl = "soon"\n'
        )
        assert (
            declared_policy_for(cfg, "production").ttl
            == DEFAULT_TTL[EnvironmentClass.Production]
        )
