from pathlib import Path

from ...database import get_db
from ..base import Base

here = Path(__file__).parent

# NOTE: this was successfully migrated from MariaDB to PostgreSQL on 2025-12-16


class Autocomplete(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        db = get_db()
        db.run_sql(here / "sql" / "autocomplete.sql")
        # TODO: synchonize macrostrat_api.autocomplete view
