"""
Subsystem for SGP matching
"""

from typer import Typer
from .match import import_sgp_data

sgp = Typer(name="sgp", no_args_is_help=True)
sgp.command(name="match-units")(import_sgp_data)
