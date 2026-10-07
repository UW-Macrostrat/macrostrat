"""Global map topology.

The command-line app lives in `commands` and is imported on first use, so the
`bounds` library can be used -- by the API, say -- without the CLI's
dependencies.
"""


def __getattr__(name):
    if name == "cli":
        from .commands import cli

        return cli
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
