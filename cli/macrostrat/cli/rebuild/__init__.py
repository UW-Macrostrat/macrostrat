from typer import Argument, Option, Typer

from ..database import get_db

rebuild = Typer(
    name="rebuild", no_args_is_help=True, short_help="Rebuild lookup tables"
)


@rebuild.command(name="lookup-units")
def lookup_units():
    """Rebuild the lookup_units table"""
    from .lookup_units import rebuild_lookup_units

    rebuild_lookup_units()
