from sys import stderr

from macrostrat.app_frame import ApplicationError
from rich.padding import Padding
from typer import Typer

from .console import err_console


class MacrostratError(ApplicationError):
    """Base class for exceptions in this module."""

    message: str
    details: str | None

    def __init__(self, message: str, details: str | None = None):
        self.message = message
        self.details = details
        super().__init__(message)

    def render(self):
        repr = f"[danger]{self.message}[/]\n"
        if self.details:
            repr += f"[details]{self.details}[/]\n"
        return repr


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
