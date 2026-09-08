"""Stage 5: the remembered environment, and how it stops being sticky.

A remembered environment lapses but is not dropped — it is kept, marked, and
confirmed before use (see `test_safety.TestRequireEnvironment`). It applies only
to the config file it was set against, and only if that file defines it.
"""

from datetime import datetime, timedelta, timezone

from pytest import fixture, mark, raises

from macrostrat.core import utils
from macrostrat.core.environment import (
    DEFAULT_TTL,
    EnvironmentClass,
    InvalidDuration,
    declared_policy_for,
    format_duration,
    parse_duration,
)
from macrostrat.core.utils import (
    ACTIVE_ENV_CONFIG_KEY,
    ACTIVE_ENV_EXPIRES_KEY,
    ACTIVE_ENV_KEY,
    ENV_EXPIRES_VAR,
    ENV_VAR,
    active_env_remaining,
    active_environment,
    extract_env_from_argv,
    normalize_macrostrat_env,
    remembered_environment,
    renew_active_env,
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
    monkeypatch.delenv(ENV_EXPIRES_VAR, raising=False)
    utils._set_active(None)
    yield state
    utils._set_active(None)


class TestArgvParsing:
    """One parser for --env. Two is how they drift."""

    @mark.parametrize(
        "args,expected,left",
        [
            (
                ["macrostrat", "--env", "staging", "db", "restore"],
                "staging",
                ["macrostrat", "db", "restore"],
            ),
            (
                ["macrostrat", "-e", "production", "db"],
                "production",
                ["macrostrat", "db"],
            ),
            (["macrostrat", "--env=staging", "db"], "staging", ["macrostrat", "db"]),
            (["macrostrat", "db", "restore"], None, ["macrostrat", "db", "restore"]),
            # A dangling flag with no value must not swallow anything.
            (["macrostrat", "--env"], None, ["macrostrat", "--env"]),
        ],
    )
    def test_extracts_and_removes_both_tokens(self, args, expected, left):
        assert extract_env_from_argv(args) == expected
        assert args == left


class TestStickiness:
    def test_local_is_remembered_indefinitely(self, app_state, config):
        set_active_env("local", expires_in=None, config_file=config)
        assert active_env_remaining() is None
        assert normalize_macrostrat_env() == "local"
        state = active_environment()
        assert state.source == "remembered"
        assert not state.lapsed

    def test_non_local_expires(self, app_state, config):
        set_active_env("production", expires_in=TTL, config_file=config)
        remaining = active_env_remaining()
        assert remaining is not None
        assert timedelta(0) < remaining <= TTL
        assert normalize_macrostrat_env() == "production"
        assert not active_environment().needs_approval

    def test_a_lapsed_environment_is_kept_and_marked(self, app_state, config):
        """Lapsing means 'ask before use', not 'drop to no environment'."""
        set_active_env(
            "production", expires_in=timedelta(seconds=-1), config_file=config
        )
        assert normalize_macrostrat_env() == "production"
        state = active_environment()
        assert state.lapsed
        assert state.needs_approval
        # Still remembered: nothing was cleared behind the operator's back.
        assert utils.get_app_state(ACTIVE_ENV_KEY) == "production"

    def test_loading_writes_nothing(self, app_state, config):
        """Config load runs for every invocation, `--help` included."""
        set_active_env(
            "production", expires_in=timedelta(seconds=-1), config_file=config
        )
        before = app_state.read_text()
        normalize_macrostrat_env()
        assert app_state.read_text() == before

    def test_an_unparseable_expiry_is_treated_as_lapsed(self, app_state, config):
        """Fail closed: a corrupt timestamp must not mean 'never expires'."""
        utils.set_app_state(ACTIVE_ENV_KEY, "production")
        utils.set_app_state(ACTIVE_ENV_EXPIRES_KEY, "not-a-timestamp")
        assert normalize_macrostrat_env() == "production"
        assert active_environment().needs_approval

    def test_a_naive_legacy_timestamp_is_read_as_local_time(self, app_state, config):
        utils.set_app_state(ACTIVE_ENV_KEY, "production")
        future = (datetime.now() + timedelta(minutes=10)).isoformat()
        utils.set_app_state(ACTIVE_ENV_EXPIRES_KEY, future)
        normalize_macrostrat_env()
        remaining = active_environment().remaining
        assert timedelta(minutes=9) < remaining <= timedelta(minutes=10)

    def test_explicit_env_is_never_subject_to_expiry(
        self, app_state, config, monkeypatch
    ):
        """--env is per-invocation by construction, so it cannot go stale."""
        set_active_env(
            "production", expires_in=timedelta(seconds=-1), config_file=config
        )
        monkeypatch.setenv(ENV_VAR, "production")
        assert normalize_macrostrat_env() == "production"
        state = active_environment()
        assert state.source == "explicit"
        assert not state.lapsed

    def test_explicit_env_overrides_a_live_remembered_one(
        self, app_state, config, monkeypatch
    ):
        set_active_env("local", expires_in=None, config_file=config)
        monkeypatch.setenv(ENV_VAR, "staging")
        assert normalize_macrostrat_env() == "staging"

    def test_a_shell_session_lapses_when_its_expiry_says_so(
        self, app_state, monkeypatch
    ):
        """An exported variable is not a way around the TTL."""
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        monkeypatch.setenv(ENV_VAR, "production")
        monkeypatch.setenv(ENV_EXPIRES_VAR, past)
        assert normalize_macrostrat_env() == "production"
        state = active_environment()
        assert state.source == "shell"
        assert state.needs_approval

    def test_a_fresh_shell_session_is_fine(self, app_state, monkeypatch):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        monkeypatch.setenv(ENV_VAR, "production")
        monkeypatch.setenv(ENV_EXPIRES_VAR, future)
        normalize_macrostrat_env()
        assert active_environment().source == "shell"
        assert not active_environment().lapsed

    def test_unsetting_clears_everything(self, app_state, config):
        set_active_env("production", expires_in=TTL, config_file=config)
        set_active_env(None)
        assert utils.get_app_state(ACTIVE_ENV_KEY) is None
        assert utils.get_app_state(ACTIVE_ENV_CONFIG_KEY) is None
        assert active_env_remaining() is None
        assert active_environment() is None

    def test_no_state_file_means_no_environment(self, app_state):
        assert not app_state.exists()
        assert normalize_macrostrat_env() is None
        assert active_environment() is None


class TestConfigScoping:
    """App state is per user; the config file is per directory."""

    def test_a_pointer_for_another_config_is_ignored_not_cleared(
        self, app_state, config, tmp_path
    ):
        other = tmp_path / "elsewhere" / "macrostrat.toml"
        set_active_env("development", expires_in=TTL, config_file=other)
        assert normalize_macrostrat_env() is None
        assert active_environment() is None
        # It still applies in the directory it was set for.
        assert utils.get_app_state(ACTIVE_ENV_KEY) == "development"
        assert remembered_environment().config_file == other

    def test_a_pointer_the_config_does_not_define_is_ignored(self, app_state, config):
        set_active_env("nonexistent", expires_in=TTL, config_file=config)
        assert normalize_macrostrat_env() is None
        assert active_environment() is None

    def test_a_legacy_pointer_without_a_config_applies(self, app_state, config):
        """State written before pointers were scoped has no config recorded."""
        utils.set_app_state(ACTIVE_ENV_KEY, "development")
        assert normalize_macrostrat_env() == "development"

    def test_a_legacy_pointer_is_still_checked_against_the_file(
        self, app_state, config
    ):
        utils.set_app_state(ACTIVE_ENV_KEY, "criticalmaas")
        assert normalize_macrostrat_env() is None

    def test_the_config_path_is_recorded_resolved(self, app_state, config):
        set_active_env("development", expires_in=TTL, config_file=config)
        assert utils.get_app_state(ACTIVE_ENV_CONFIG_KEY) == str(config.resolve())


class TestRenewal:
    def test_renew_restamps_the_expiry_and_approves(self, app_state, config):
        set_active_env(
            "production", expires_in=timedelta(seconds=-1), config_file=config
        )
        normalize_macrostrat_env()
        assert active_environment().needs_approval
        expires = renew_active_env(TTL)
        state = active_environment()
        assert not state.lapsed
        assert state.approved
        assert timedelta(0) < state.remaining <= TTL
        # Persisted, so the next invocation is fresh too.
        assert active_env_remaining() > timedelta(0)
        assert expires is not None

    def test_renew_to_never(self, app_state, config):
        set_active_env(
            "production", expires_in=timedelta(seconds=-1), config_file=config
        )
        normalize_macrostrat_env()
        assert renew_active_env(None) is None
        assert active_environment().remaining is None
        assert active_env_remaining() is None

    def test_renewing_a_shell_session_persists_nothing(self, app_state, monkeypatch):
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        monkeypatch.setenv(ENV_VAR, "production")
        monkeypatch.setenv(ENV_EXPIRES_VAR, past)
        normalize_macrostrat_env()
        renew_active_env(TTL)
        assert active_environment().approved
        assert not app_state.exists()

    def test_renew_without_an_environment_is_a_noop(self, app_state):
        assert renew_active_env(TTL) is None


class TestDurations:
    @mark.parametrize(
        "value,expected",
        [
            ("15m", timedelta(minutes=15)),
            ("15 min", timedelta(minutes=15)),
            ("8h", timedelta(hours=8)),
            ("2h30m", timedelta(hours=2, minutes=30)),
            ("1d", timedelta(days=1)),
            ("90s", timedelta(seconds=90)),
            ("45", timedelta(minutes=45)),
            (45, timedelta(minutes=45)),
            (2.5, timedelta(minutes=2, seconds=30)),
            ("never", None),
            ("NONE", None),
            (False, None),
            (None, None),
        ],
    )
    def test_parses(self, value, expected):
        assert parse_duration(value) == expected

    @mark.parametrize("bad", ["soon", "0m", "-5m", 0, -1, True, "h"])
    def test_rejects_junk(self, bad):
        with raises(InvalidDuration):
            parse_duration(bad)

    @mark.parametrize(
        "value,text",
        [
            (None, "never"),
            (timedelta(minutes=15), "15 min"),
            (timedelta(hours=8), "8 h"),
            (timedelta(hours=2, minutes=30), "2 h 30 min"),
            (timedelta(days=1, hours=1), "1 d 1 h"),
            (timedelta(seconds=30), "30 s"),
        ],
    )
    def test_formats(self, value, text):
        assert format_duration(value) == text


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
        from macrostrat.core.environment import EnvironmentPolicy

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
