"""
Subsystem for SGP matching
"""

from typer import Typer

from macrostrat.cli.database import get_db

from .match import log_matches, match_sgp_data_cmd
from .migrations import *
from .paleogeography import compute_paleo_positions
from .utils import get_sgp_db

sgp = Typer(
    name="sgp",
    no_args_is_help=True,
    short_help="Sedimentary Geochemistry and Paleogeography integration",
)
sgp.command(name="match-units")(match_sgp_data_cmd)
sgp.command(name="paleogeography")(compute_paleo_positions)
sgp.command(name="log-matches")(log_matches)


@sgp.command("import-data")
def import_sgp_data():
    """
    Import SGP sample and analysis data.
    """

    db = get_db()

    sql_dir = Path(__file__).parent / "sql"

    sgp_db = get_sgp_db()

    print("Importing SGP data...")
    print(sgp_db.engine.url)

    db.run_sql(
        sql_dir / "create-fdw.sql",
        dict(
            sgp_host=sgp_db.engine.url.host,
            sgp_port=str(sgp_db.engine.url.port or 5432),
            sgp_database=sgp_db.engine.url.database,
            sgp_user=sgp_db.engine.url.username,
            sgp_password=sgp_db.engine.url.password,
        ),
    )

    db.run_sql(sql_dir / "copy-sgp-data.sql")

    db.run_sql("DROP SCHEMA IF EXISTS sgp CASCADE;")
    db.run_sql("DROP SERVER IF EXISTS sgp_server CASCADE;")
    print("SGP data import complete.")
