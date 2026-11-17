"""The active environment's policy, read from Macrostrat's settings.

Classes, confirmation levels and time-to-live are defined by
`macrostrat.app_frame.environments`; this adapts Macrostrat's two settings
objects and its config file to it.
"""

from typing import Optional

from macrostrat.app_frame.environments import (
    DEFAULT_ENV,
    EnvironmentPolicy,
    policy_from_table,
    read_config,
)
from macrostrat.app_frame.environments.policy import (
    ACTIVE_TTL_KEY,
    CONFIRM_KEY,
    ENV_CLASS_KEY,
    WRITE_GATE_KEY,
)


def policy_from_settings(settings) -> EnvironmentPolicy:
    """Resolve the active environment's policy from a settings object."""
    name = getattr(settings, "env", None)
    if name == DEFAULT_ENV:
        # `default` is the base layer, never a selectable environment.
        name = None
    return EnvironmentPolicy.resolve(
        name,
        env_class=settings.get(ENV_CLASS_KEY, None),
        write_gate=settings.get(WRITE_GATE_KEY, None),
        active_ttl=settings.get(ACTIVE_TTL_KEY, None),
        confirm=settings.get(CONFIRM_KEY, None),
    )


def declared_policy_for(config_file, env_name: Optional[str]) -> EnvironmentPolicy:
    """Resolve *env_name*'s policy by reading the TOML directly.

    Deciding whether a remembered environment may still be used has to happen
    before settings are built, and building them needs the environment.
    """
    table = {}
    if env_name is not None:
        table = read_config(config_file).get(env_name, None)
    return policy_from_table(env_name, table)
