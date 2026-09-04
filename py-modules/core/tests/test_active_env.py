"""Stage 5: the remembered environment, and how it stops being sticky."""

from datetime import datetime, timedelta

from pytest import fixture, mark

from macrostrat.core import utils
from macrostrat.core.environment import EnvironmentClass, declared_policy_for
from macrostrat.core.utils import (
    ACTIVE_ENV_EXPIRES_KEY,
    ACTIVE_ENV_KEY,
    NON_LOCAL_TTL,
    active_env_remaining,
    extract_env_from_argv,
    normalize_macrostrat_env,
    set_active_env,
)


@fixture
def app_state(tmp_path, monkeypatch):
    """Isolate app-state.toml, and clear MACROSTRAT_ENV."""
    state = tmp_path / "app-state.toml"
    monkeypatch.setattr(utils, "get_app_state_file", lambda: state)
    monkeypatch.delenv("MACROSTRAT_ENV", raising=False)
    return state


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
    def test_local_is_remembered_indefinitely(self, app_state):
        set_active_env("local", expires_in=None)
        assert active_env_remaining() is None
        assert normalize_macrostrat_env() == "local"

    def test_non_local_expires(self, app_state):
        set_active_env("production", expires_in=NON_LOCAL_TTL)
        remaining = active_env_remaining()
        assert remaining is not None
        assert timedelta(0) < remaining <= NON_LOCAL_TTL
        assert normalize_macrostrat_env() == "production"

    def test_a_lapsed_environment_is_ignored_and_cleared(self, app_state):
        set_active_env("production", expires_in=timedelta(seconds=-1))
        assert normalize_macrostrat_env() is None
        # And it is forgotten, so it cannot come back.
        assert utils.get_app_state(ACTIVE_ENV_KEY) is None

    def test_an_unparseable_expiry_is_treated_as_lapsed(self, app_state):
        """Fail closed: a corrupt timestamp must not mean 'never expires'."""
        utils.set_app_state(ACTIVE_ENV_KEY, "production")
        utils.set_app_state(ACTIVE_ENV_EXPIRES_KEY, "not-a-timestamp")
        assert normalize_macrostrat_env() is None

    def test_explicit_env_is_never_subject_to_expiry(self, app_state, monkeypatch):
        """--env is per-invocation by construction, so it cannot go stale."""
        set_active_env("production", expires_in=timedelta(seconds=-1))
        monkeypatch.setenv("MACROSTRAT_ENV", "production")
        assert normalize_macrostrat_env() == "production"

    def test_explicit_env_overrides_a_live_remembered_one(self, app_state, monkeypatch):
        set_active_env("local", expires_in=None)
        monkeypatch.setenv("MACROSTRAT_ENV", "staging")
        assert normalize_macrostrat_env() == "staging"

    def test_unsetting_clears_both_keys(self, app_state):
        set_active_env("production", expires_in=NON_LOCAL_TTL)
        set_active_env(None)
        assert utils.get_app_state(ACTIVE_ENV_KEY) is None
        assert active_env_remaining() is None

    def test_no_state_file_means_no_environment(self, app_state):
        assert not app_state.exists()
        assert normalize_macrostrat_env() is None


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
