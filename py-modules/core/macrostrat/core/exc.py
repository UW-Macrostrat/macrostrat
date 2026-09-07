from rich.padding import Padding
from typer import Typer

from macrostrat.utils import ApplicationError

from .console import err_console


class MacrostratError(ApplicationError):
    """Base class for exceptions in this module."""


class UnknownEnvironment(MacrostratError):
    """An environment was named that the config file does not define.

    Raised for an explicit `--env` or an exported `MACROSTRAT_ENV`. Dynaconf
    itself accepts any name and quietly yields an empty environment, which used
    to surface much later as a database error about a `None` URL.
    """

    def __init__(self, name: str, available, config_file=None):
        self.name = name
        self.available = list(available)
        self.config_file = config_file
        where = f" in {config_file}" if config_file else ""
        details = "Available environments:\n" + "\n".join(
            f"- {env}" for env in self.available
        )
        if not self.available:
            details = f"No environments are defined{where}."
        super().__init__(
            f"Environment '{name}' is not defined{where}",
            details,
        )


class ConfigError(MacrostratError):
    """The configuration file could not be read, or failed validation.

    Raised by the version-2 loader with the file's problems rendered as
    details, so a mistyped or removed key is reported before anything runs.
    """


## We should standardize this
def setup_exception_handling(app: Typer):
    def wrapped_app():
        try:
            app()
        except ApplicationError as error:
            rendered = Padding(error.render(), (1, 2))
            err_console.print(rendered)
            exit(1)

    return wrapped_app
