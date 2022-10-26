from pathlib import Path
from macrostrat.utils import relative_path
from rich import print
from ..database import db


def upgrade_db():
    """Upgrade the database to the latest version"""

    print("Connected to [dim green]" + str(db.engine.url))

    filename = Path(relative_path(__file__, "procedures", "update-srid.sql"))
    db.exec_sql(filename)
