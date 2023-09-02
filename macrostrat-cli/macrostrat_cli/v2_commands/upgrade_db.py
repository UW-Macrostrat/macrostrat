from pathlib import Path
from macrostrat.utils import relative_path
from rich import print
from os import environ

from ..database import get_db


def upgrade_db():
    """Apply PostgreSQL database upgrades to bring Macrostrat to the v2 standard"""

    db = get_db()

    print(
        f"Connected to [dim green]{db.engine.url.database}[/dim green] on port [dim green]{db.engine.url.port}[/dim green]"
    )
    files = Path(relative_path(__file__, "procedures")).glob("*.sql")
    files = list(files)
    files.sort()

    for file in files:
        list(db.run_sql(file))


def extend_schema():
    """Extend the Macrostrat database schema to include new tables and columns"""

    db = get_db()
    print(
        f"Connected to [dim green]{db.engine.url.database}[/dim green] on port [dim green]{db.engine.url.port}[/dim green]"
    )

    ext_dir = environ.get("MACROSTRAT_SCHEMA_EXTENSIONS")
    if ext_dir is None:
        raise ValueError("MACROSTRAT_SCHEMA_EXTENSIONS environment variable not set")

    files = Path(ext_dir).glob("*.sql")
    files = list(files)
    files.sort()

    for file in files:
        list(db.run_sql(file))
