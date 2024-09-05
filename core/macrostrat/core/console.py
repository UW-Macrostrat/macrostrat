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
