from pathlib import Path

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
