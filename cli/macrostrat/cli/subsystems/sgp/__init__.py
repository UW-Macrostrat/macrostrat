"""
Subsystem for SGP matching
"""

from typer import Typer

from .match import import_sgp_data
from .paleogeography import compute_paleo_positions

sgp = Typer(
    name="sgp",
    no_args_is_help=True,
    short_help="Sedimentary Geochemistry and Paleogeography integration",
)
sgp.command(name="match-units")(import_sgp_data)
sgp.command(name="paleogeography")(compute_paleo_positions)
