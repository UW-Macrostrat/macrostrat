from rich.console import Console
from typer import Option, Typer

cli = Typer(help="Rebuild database tools")
console = Console()


def _get_scripts() -> dict:
    from .scripts import (
        Autocomplete,
        LookupStratNames,
        LookupUnitAttrsApi,
        LookupUnitIntervals,
        LookupUnits,
        Stats,
        StratNameFootprints,
        UnitBoundaries,
    )

    return {
        "autocomplete": Autocomplete,
        "lookup-strat-names": LookupStratNames,
        "lookup-unit-attrs-api": LookupUnitAttrsApi,
        "lookup-unit-intervals": LookupUnitIntervals,
        "lookup-units": LookupUnits,
        "stats": Stats,
        "strat-name-footprints": StratNameFootprints,
        "unit-boundaries": UnitBoundaries,
    }


@cli.command()
def scripts(
    name: str | None = Option(
        None, "--name", "-n", help="Run a specific script by name"
    ),
    list_: bool = Option(False, "--list", "-l", help="List available scripts"),
):
    """Run rebuild scripts."""
    all_scripts = _get_scripts()

    if list_:
        for n in all_scripts:
            console.print(f"  [cyan]{n}[/]")
        return

    to_run = {name: all_scripts[name]} if name else all_scripts

    if name and name not in all_scripts:
        raise RuntimeError(
            f"No script named '{name}'. Available: {', '.join(all_scripts)}"
        )

    for script_name, cls in to_run.items():
        console.print(f"[bold cyan]→ {script_name}[/]")
        cls().run()
        console.print(f"[green]✓ done[/]")
