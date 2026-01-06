import os
from pathlib import Path

from macrostrat.core.database import get_database
from typer import Typer

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


pipeline_dir = Path(__file__).parent / "pipeline"
ingest_dir = Path("/Users/Daven/Projects/Macrostrat/Datasets/GBDB workshop")


@app.command()
def run_pipeline():
    """
    Run the data ingestion pipeline
    """

    runnables = []
    for ext in [".py", ".sql", ".sh"]:
        runnables.extend(pipeline_dir.glob(f"*{ext}"))

    for runnable in sorted(runnables):
        print(f"Running {runnable.name}...")
        ROOT_DIR = ingest_dir
        os.environ["ROOT_DIR"] = str(ROOT_DIR)
        if runnable.suffix == ".py":
            exec(runnable.read_text(), globals())
        elif runnable.suffix == ".sql":
            db = get_database()
            db.run_sql(runnable)
        elif runnable.suffix == ".sh":
            import subprocess

            subprocess.run(["bash", str(runnable)], check=True)
        else:
            print(f"Unknown file type: {runnable.suffix}")
