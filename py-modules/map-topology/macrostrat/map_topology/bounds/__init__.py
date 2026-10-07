"""Map boundaries composed from ordered operations.

`build`, `edit` and `operations` need only a database and pydantic; the CLI, in
`commands`, is imported on first use.
"""


def __getattr__(name):
    if name == "cli":
        from .commands import cli

        return cli
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
