"""
Subsystem for SGP matching
"""

from typer import Typer

from macrostrat.cli.database import get_db
from .match import import_sgp_data, log_matches
from .migrations import *
from .paleogeography import compute_paleo_positions

sgp = Typer(
    name="sgp",
    no_args_is_help=True,
    short_help="Sedimentary Geochemistry and Paleogeography integration",
)
sgp.command(name="match-units")(import_sgp_data)
sgp.command(name="paleogeography")(compute_paleo_positions)
sgp.command(name="log-matches")(log_matches)


@sgp.command("import-data")
def import_sgp_data():
    """
    Import SGP sample and analysis data.
    """

    db = get_db()

    sql_dir = Path(__file__).parent / "sql"

    db.run_sql(sql_dir / "create-fdw.sql")
    db.run_sql(sql_dir / "copy-sgp-data.sql")
