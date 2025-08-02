from macrostrat.database import Database
from macrostrat.utils import relative_path, cmd
from pathlib import Path
from os import environ
from rich import print
from typer import Typer
from dotenv import load_dotenv
from sqlalchemy.sql import text
from datetime import datetime
from psycopg2.sql import Literal

load_dotenv()

app = Typer(no_args_is_help=True)

app.command()


@app.command()
def run(truncate: bool = False):
    """Run the update procedure."""
    tileserver_db = environ.get("TILESERVER_STATS_DATABASE")
    db = Database(tileserver_db)

    # Run update
    fn = Path(relative_path(__file__, "procedures")) / "run-update.sql"
    sql = text(fn.read_text().replace(":", "\:"))


    # check query timing
    conn = db.engine.connect()
    n_results = 10000
    start = datetime.now()
    step = start
    while n_results > 0:
        res = conn.execute(sql, execution_options=dict(no_parameters=True)).first()
        n_results = res.n_rows
        conn.execute(text("COMMIT"))
        next_step = datetime.now()
        dt = (next_step - step).total_seconds()
        print(f"{res.last_row_id} ({dt*1000:.0f} ms)")
        step = next_step

    if truncate and n_results == 0:
        conn.execute(text("TRUNCATE TABLE requests"))

    print(f"Total time: {datetime.now() - start}")


@app.command()
def reset(drop: bool = False):
    """Empty the stats schema and re-run the schema creation scripts."""
    tileserver_db = environ.get("TILESERVER_STATS_DATABASE")
    db = Database(tileserver_db)

    if drop:
        db.engine.execute("DROP SCHEMA IF EXISTS stats CASCADE")

    files = Path(relative_path(__file__, "schema")).glob("*.sql")
    files = list(files)
    files.sort()

    for file in files:
        list(db.run_sql(file))

@app.command()
def truncate():
    """Create the stats schema."""
    tileserver_db = environ.get("TILESERVER_STATS_DATABASE")
    db = Database(tileserver_db)

    files = Path(relative_path(__file__, "schema")).glob("*.sql")
    files = list(files)
    files.sort()

    for file in files:
        list(db.run_sql(file))
