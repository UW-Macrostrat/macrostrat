"""The core of the Macrostrat system.

`app`, `get_database` and `SchemaDefinition` are resolved **lazily**, on first
attribute access, rather than at import time.

They used to be built in this module's body, which meant that importing *any*
submodule of `macrostrat.core` — even a pure, side-effect-free one — located and
loaded `macrostrat.toml`, applied every one of `config.py`'s environment
side effects, and called `sys.exit(1)` when no config file was present. That made
helpers in this package impossible to import in a test, in a subprocess, or in
any context without a fully-provisioned config.

The lazy hooks below keep every existing call site working unchanged
(`from macrostrat.core import app` behaves exactly as before, and still loads
config before `get_database` / `SchemaDefinition` are resolved) while letting
`macrostrat.core.environment`, `macrostrat.core.secrets` and friends be imported
on their own.
"""

from .main import Macrostrat  # noqa: F401

# Deliberately *not* published into this module's globals once built: the CLI
# test suite calls importlib.reload() on this module and expects the next `app`
# access to construct a fresh application. Caching in globals() would survive
# the reload (reload re-executes the body into the same module dict without
# clearing it) and hand back a stale app bound to the previous config.
_app = None

__all__ = ["Macrostrat", "app", "get_database", "SchemaDefinition"]


def _get_app() -> Macrostrat:
    global _app
    if _app is None:
        _app = Macrostrat()
    return _app


def __getattr__(name):
    """Resolve the config-dependent names on first access (PEP 562)."""
    if name == "app":
        return _get_app()

    if name in ("get_database", "SchemaDefinition"):
        # These must not be imported before the application's config has been
        # loaded — the original module body enforced that by ordering.
        _get_app()
        if name == "get_database":
            from .database import get_database

            return get_database
        from .schema_definition import SchemaDefinition

        return SchemaDefinition

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(__all__)
