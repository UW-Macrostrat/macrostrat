from macrostrat.database import Database
from pathlib import Path
import inspect

class Migration:
    """This will eventually be merged with the migration system in macrostrat.dinosaur"""

    name: str
    description: str
    subsystem: str
    expected_tables : list[str] = []

    def should_apply(self, database: Database):
        """ Determine whether this migration needs to be run. By default, check that every table in
        `self.expected_tables` exists. """
        insp = database.inspector
        for table_name in self.expected_tables:
            table, schema = table_name.split('.')
            if not insp.has_table(table, schema=schema):
                return True
        return False

    def apply(self, database: Database):
        """ Apply the migrations defined by this class. By default, run every sql file 
        in the same directory as the class definition. """
        __dir__ = Path(inspect.getfile(self.__class__)).parent
        database.run_fixtures(__dir__)

    def is_satisfied(self, database: Database):
        """In some cases, we may want to note that a migration does not need to be run
        (e.g. if the database is already in the correct state) without actually running it.
        """
        return not self.should_apply(database)
