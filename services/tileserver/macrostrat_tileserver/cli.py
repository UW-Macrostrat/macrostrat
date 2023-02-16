from os import environ
from macrostrat.database import Database
from macrostrat.utils import relative_path
from typer import Typer
from dotenv import load_dotenv

load_dotenv()

# Config loading

here = relative_path(__file__)
root = (here).resolve()

db_url = environ.get("DATABASE_URL")

# App
_cli = Typer()


@_cli.command()
def sync():
    fixtures_dir = root / "fixtures"

    db = Database(db_url)

    files = list(fixtures_dir.glob("*.sql"))
    files.sort()
    for fn in files:
        list(db.run_sql(fn))
