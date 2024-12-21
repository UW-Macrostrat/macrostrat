from rich.padding import Padding
from typer import Typer

from macrostrat.utils import ApplicationError

from .console import err_console


class MacrostratError(ApplicationError):
    """Base class for exceptions in this module."""


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
