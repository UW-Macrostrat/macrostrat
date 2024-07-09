from macrostrat.database import Database


class Migration:
    """This will eventually be merged with the migration system in macrostrat.dinosaur"""

    name: str
    description: str
    subsystem: str

    def __init__(self, db: Database):
        self.db = db

    def should_apply(self, database: Database):
        raise NotImplementedError

    def apply(self, database: Database):
        raise NotImplementedError
