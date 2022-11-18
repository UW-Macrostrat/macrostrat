from macrostrat.database import Database
from macrostrat.utils import relative_path, cmd
from pathlib import Path
from os import environ
from rich import print
from typer import Typer
from dotenv import load_dotenv

load_dotenv()

app = Typer(no_args_is_help=True)

app.command()


@app.command()
def create_tables():

    tileserver_db = environ.get("TILESERVER_STATS_DATABASE")
    db = Database(tileserver_db)

    files = Path(relative_path(__file__, "schema")).glob("*.sql")
    files = list(files)
    files.sort()

    for file in files:
        list(db.run_sql(file))
