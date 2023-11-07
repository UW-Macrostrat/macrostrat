from os import environ
from macrostrat.database import Database
from macrostrat.utils import relative_path
from typer import Typer
from dotenv import load_dotenv

load_dotenv()

# Config loading

here = relative_path(__file__)
root = (here).resolve()


# App
_cli = Typer(no_args_is_help=True, name="tileserver")


@_cli.command(name="create-fixtures")
def create_fixtures():
    """Create database fixtures"""
    fixtures_dir = root / "fixtures"
    db_url = environ.get("DATABASE_URL")

    db = Database(db_url)

    files = list(fixtures_dir.glob("*.sql"))
    files.sort()
    for fn in files:
        list(db.run_sql(fn))


@_cli.command(name="list-layers")
def list_layers():
    """List available map layers"""
    from .main import app

    for k, v in app.state.function_catalog.funcs.items():
        print(k)
        print(v)
        print()
