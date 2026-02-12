from pathlib import Path
from typer import Typer, Argument

app = Typer(
    no_args_is_help=True,
    help="Column ingestion subsystem for Macrostrat",
)

@app.command()
def ingest_columns(data_file: Path = Argument(..., help="Path to the data file to ingest")):
    """Ingest columns tabular data."""
    print("Ingesting columns...")



