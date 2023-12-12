from macrostrat.database import run_sql
from macrostrat.utils import relative_path
from pathlib import Path
from rich.progress import Progress
from rich.console import Console
from sqlalchemy import text

query_file = Path(relative_path(__file__, "sql", "carto-plate-index-cache.sql"))

console = Console()


def build_carto_plate_index(db):
    """Build a representation of the Carto map layers, split by plate polygons"""

    count = run_sql(db, "SELECT COUNT(*) FROM carto.polygons")[0].scalar()
    console.print(f"Carto layers contain {count} polygons")

    chunk_size = 1000
    query = text(query_file.read_text())

    with Progress() as progress:
        task = progress.add_task("Building Carto plate cache", total=count)

        conn = db.engine.connect()
        last_id = -1
        while last_id is not None:
            last_id = conn.execute(
                query, last_id=last_id, chunk_size=chunk_size
            ).scalar()
            progress.update(task, advance=chunk_size)

    console.print("Done!")
