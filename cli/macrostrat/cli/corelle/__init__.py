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
    for scale in ["tiny", "small", "medium"]:
        build_carto_plate_index_for_scale(db, scale)


def build_carto_plate_index_for_scale(db, scale):
    """Build a representation of the Carto map layers, split by plate polygons"""
    count = db.run_query(
        "SELECT COUNT(*) FROM carto.polygons WHERE scale = :scale", dict(scale=scale)
    ).scalar()
    console.print(f"Carto layer contains {count} polygons at scale {scale}")

    chunk_size = 1000
    query = text(query_file.read_text())

    with Progress() as progress:
        task = progress.add_task(
            f"Building Carto plate cache for scale {scale}", total=count
        )

        last_id = -1
        while last_id is not None:
            last_id = db.session.execute(
                query, params=dict(last_row=last_id, chunk_size=chunk_size, scale=scale)
            ).scalar()
            db.session.commit()
            progress.update(task, advance=chunk_size)

    console.print("Done!")

fixtures = Path(relative_path(__file__, "fixtures"))

def create_corelle_fixtures(db):
    db.run_fixtures(fixtures)