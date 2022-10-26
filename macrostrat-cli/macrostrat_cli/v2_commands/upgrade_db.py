from pathlib import Path
from macrostrat.utils import relative_path
from rich import print

from ..database import db


def upgrade_db():
    """Apply PostgreSQL database upgrades to bring Macrostrat to the v2 standard"""

    print(
        f"Connected to [dim green]{db.engine.url.database}[/dim green] on port [dim green]{db.engine.url.port}[/dim green]"
    )
    files = Path(relative_path(__file__, "procedures")).glob("*.sql")
    files = list(files)
    files.sort()

    for file in files:
        db.exec_sql(file)
