from pathlib import Path

from typer import Typer

from macrostrat.core.database import get_database

app = Typer(
    name="gbdb",
    no_args_is_help=True,
    short_help="Geologic map database integration",
)


def update_age_model():
    """
    Stack units by age
    """
    db = get_database()

    res = db.run_query("SELECT count(*) FROM macrostrat_gbdb.strata").scalar()
    print(res)


@app.command("ingest")
def ingest_strata(source: Path):
    from .ingest_strata import ingest_strata

    ingest_strata(source)
