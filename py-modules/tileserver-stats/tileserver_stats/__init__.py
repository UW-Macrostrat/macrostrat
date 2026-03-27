from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from macrostrat.database.transfer import move_tables
from rich import print
from sqlalchemy.sql import text
from typer import Typer

from macrostrat.database import Database
from macrostrat.utils import relative_path
from macrostrat.core.config import settings
from macrostrat.core import get_database
import asyncio

load_dotenv()

app = Typer(no_args_is_help=True, short_help="Compile tileserver statistics")


@app.command(name="compute")
def compute_stats(truncate: bool = False):
    """Run the update procedure."""
    tileserver_db = settings.databases.get("tileserver_stats")
    db = Database(tileserver_db)

    # Run update
    fn = Path(relative_path(__file__, "procedures")) / "run-update.sql"
    sql = text(fn.read_text().replace(":", r"\:"))

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
def integrate_schema(drop: bool = False):
    """Merge the tileserver_stats schema into the core Macrostrat database."""
    tileserver_db = settings.databases.get("tileserver_stats")

    tdb = Database(tileserver_db)
    # Rename the schema stats to tileserver_stats
    tdb.run_sql("ALTER SCHEMA stats RENAME TO tileserver_stats")

    # Move the `requests` table into the `tileserver_stats` schema
    tdb.run_sql("ALTER TABLE requests SET SCHEMA tileserver_stats")

    # Switch to SQL in Macrostrat database
    db = get_database()
    # Merge the `tileserver_stats` schema into the core Macrostrat database

    task = move_tables(tdb.engine, db.engine, schemas=["tileserver_stats"])
    asyncio.run(task)


@app.command()
def show_database():
    """Show the database connection string."""
    tileserver_db = settings.databases.get("tileserver_stats")
    print(tileserver_db)
