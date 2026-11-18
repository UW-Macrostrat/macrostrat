"""The active environment's policy, read from a settings object.

Classes and confirmation levels are tested in `macrostrat.app_frame`.
"""

from pytest import mark

from macrostrat.app_frame.environments import (
    DEFAULT_GATES,
    AccessScope,
    EnvironmentClass,
    EnvironmentPolicy,
    WriteGate,
    parse_gate,
)
from macrostrat.core.environment import policy_from_settings


class _Settings(dict):
    """Minimal stand-in for the settings object's read surface."""

    def __init__(self, env=None, **values):
        super().__init__(values)
        self.env = env

    def get(self, key, default=None):
        return super().get(key, default)


class TestPolicyFromSettings:
    def test_reads_class_and_gates(self):
        p = policy_from_settings(
            _Settings(
                env="staging", env_class="staging", write_gate={"data": "confirm"}
            )
        )
        assert p.env_class == EnvironmentClass.Staging
        assert p.gate_for(AccessScope.Data) == WriteGate.Confirm

    def test_default_env_is_not_an_environment(self):
        p = policy_from_settings(_Settings(env="default"))
        assert p.name is None
        assert p.env_class == EnvironmentClass.Production

    def test_frozen(self):
        from dataclasses import FrozenInstanceError

        from pytest import raises

        p = policy_from_settings(_Settings(env="local"))
        with raises(FrozenInstanceError):
            p.env_class = EnvironmentClass.Local
