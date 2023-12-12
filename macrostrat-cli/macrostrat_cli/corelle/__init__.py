from macrostrat.database import run_sql
from macrostrat.utils import relative_path
from pathlib import Path
from rich.progress import Progress

query_file = Path(relative_path(__file__, "sql", "carto-plate-index-cache.sql"))


def build_carto_plate_index(db):
    """Build a representation of the Carto map layers, split by plate polygons"""

    count = run_sql(db, "SELECT COUNT(*) FROM carto.polygons")[0].scalar()
    print(f"Carto layers contain {count} polygons")

    chunk_size = 1000

    with Progress() as progress:
        task = progress.add_task("Building Carto plate cache", total=count)

        last_id = -1
        while last_id is not None:
            last_id = run_sql(
                db,
                query_file,
                params={"last_id": last_id, "chunk_size": chunk_size},
            )[0].scalar()
            progress.update(task, advance=chunk_size)
