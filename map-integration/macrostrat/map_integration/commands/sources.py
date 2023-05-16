from rich.console import Console
from rich.table import Table
from ..database import db


def map_sources():
    """List all available map sources"""
    sources = db.session.execute(
        "SELECT source_id, primary_table, name FROM maps.sources"
    ).fetchall()

    table = Table(title="Macrostrat map sources")

    table.add_column("id", justify="right", style="cyan", no_wrap=True)
    table.add_column("key", justify="right", style="cyan", no_wrap=True)
    table.add_column("name")

    for source in sources:
        table.add_row(str(source.source_id), source.primary_table, source.name)

    console = Console()
    console.print(table)
