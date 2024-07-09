from macrostrat.database import Database


class Migration:
    """This will eventually be merged with the migration system in macrostrat.dinosaur"""

    name: str
    description: str
    subsystem: str

    def should_apply(self, database: Database):
        raise NotImplementedError

    def apply(self, database: Database):
        raise NotImplementedError

    def is_satisfied(self, database: Database):
        """In some cases, we may want to note that a migration does not need to be run
        (e.g. if the database is already in the correct state) without actually running it.
        """
        return not self.should_apply(database)
