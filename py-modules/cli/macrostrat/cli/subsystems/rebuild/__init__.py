from rich.console import Console
from typer import Option, Typer
from macrostrat.core.database import get_database

from .utils import grant_permissions

cli = Typer(help="Rebuild scripts tools", no_args_is_help=True)

console = Console()


def _get_scripts() -> dict:
    from .scripts import (
        autocomplete,
        lookup_strat_names,
        lookup_unit_attrs_api,
        lookup_unit_intervals,
        lookup_units,
        stats,
        strat_name_footprints,
        unit_boundaries,
    )

    commands = {
        "autocomplete": autocomplete,
        "lookup-strat-names": lookup_strat_names,
        "lookup-unit-attrs-api": lookup_unit_attrs_api,
        "lookup-unit-intervals": lookup_unit_intervals,
        "lookup-units": lookup_units,
        "stats": stats,
        "strat-name-footprints": strat_name_footprints,
        "unit-boundaries": unit_boundaries,
    }

    return {k: wrap_command(v) for k, v in commands.items()}


mark_slow = ("strat-name-footprints",)


def is_column_script(name):
    return "unit" in name


def wrap_command(command_func):
    """Decorator to wrap command functions with logging and permission granting"""

    def wrapper():
        command_func()
        console.print(f"[dim]  granting permissions...[/]")
        grant_permissions(get_database())
        console.print(f"[green]✓ done[/]\n")

    wrapper.__doc__ = command_func.__doc__

    return wrapper


_scripts = _get_scripts()

for name, cls in _scripts.items():
    short_help = cls.__doc__.splitlines()[0]
    if name in mark_slow:
        short_help += " [dim red](slow)[/]"
    cli.command(name=name, help=short_help)(cls)


column_help = "Run column-related rebuild scripts:\n" + "\n".join(
    [f"    [dim]- {name}[/]" for name in _scripts.keys() if is_column_script(name)]
)


@cli.command(
    rich_help_panel="Meta",
    name="columns",
    help=column_help,
)
def columns():
    """Run column-related rebuild scripts."""
    for name, command in _scripts.items():
        if is_column_script(name):
            console.print(f"[bold cyan]→ {name}[/]")
            command()


@cli.command(rich_help_panel="Meta", name="all", help="Run all rebuild scripts")
def all():
    """Run all rebuild scripts."""
    for name, command in _scripts.items():
        console.print(f"[bold cyan]→ {name}[/]")
        command()
