from pathlib import Path

from ...database import get_db
from ..base import Base

here = Path(__file__).parent


class Stats(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        db = get_db()
        db.run_sql(here / "sql" / "stats.sql")
