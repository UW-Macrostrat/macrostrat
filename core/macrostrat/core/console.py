from textwrap import dedent

from rich.console import Console
from rich.theme import Theme

console_theme = Theme(
    {
        "info": "dim cyan",
        "warning": "magenta",
        "danger": "bold red",
        "item": "bold blue",
        "details": "dim",
        "success": "green",
    }
)

err_console = Console(theme=console_theme, stderr=True)


def echo(*args, **kwargs):
    console = kwargs.pop("console", err_console)
    args1 = [dedent(arg) if isinstance(arg, str) else arg for arg in args]
    console.print(*args1, **kwargs)
