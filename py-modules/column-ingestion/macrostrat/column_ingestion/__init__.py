from pathlib import Path

from typer import Argument, Typer

app = Typer(
    no_args_is_help=True,
    help="Column ingestion subsystem for Macrostrat",
)


@app.command(name="ingest")
def ingest_columns(
    data_file: Path = Argument(..., help="Path to the data file to ingest")
):
    """Ingest columns tabular data."""
    from .ingest import ingest_columns_from_file

    ingest_columns_from_file(data_file)
