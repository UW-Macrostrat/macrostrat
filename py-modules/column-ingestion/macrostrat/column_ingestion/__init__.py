from pathlib import Path
from macrostrat.core.database import get_database

from typer import Argument, Typer

from .project_metadata import shanan_column_importer

app = Typer(
    no_args_is_help=True,
    help="Column ingestion subsystem for Macrostrat",
)


@app.command(name="ingest")
def ingest_columns(
    data_file: Path = Argument(..., help="Path to the data file to ingest")
):
    """Ingest columns from tabular data."""
    from .ingest import ingest_columns_from_file

    db = get_database()
    ingest_columns_from_file(db, data_file)


app.command("ingest-shanan")(shanan_column_importer)


@app.command(name="calculate-age-model")
def calculate_age_model(
    col_id: int = Argument(..., help="Column ID for which to calculate the age model")
):
    """Calculate age model for columns in the data file."""
    from .age_model import build_age_model_for_existing_column

    db = get_database()
    build_age_model_for_existing_column(db, col_id)
