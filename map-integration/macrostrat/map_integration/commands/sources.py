from rich.console import Console
from rich.table import Table

from ..database import get_database


def map_sources():
    """List all available map sources"""
    db = get_database()
    sources = db.run_query(
        "SELECT source_id, slug, name FROM maps.sources ORDER BY source_id DESC"
    ).fetchall()

    table = Table(title="Macrostrat map sources")

    table.add_column("id", justify="right", style="cyan", no_wrap=True)
    table.add_column("key", justify="right", style="cyan", no_wrap=True)
    table.add_column("name")

    for source in sources:
        table.add_row(str(source.source_id), source.slug, source.name)

    console = Console()
    console.print(table)
