from macrostrat.database import Database
from pathlib import Path
import inspect
from typing import Callable
from enum import Enum

DbEvaluator = Callable[[Database], bool]

""" Higher-order function that returns """
def exists(*table_names: str):
    def _exists(db: Database):
        for table_name in table_names:
            schema, table = table_name.split('.')
            if not db.inspector.has_table(table, schema=schema):
                return False
        return True
    return _exists

def not_exists(*table_names: str):
    def _not_exists(db: Database):
        for table_name in table_names:
            schema, table = table_name.split('.')
            if db.inspector.has_table(table, schema=schema):
                return False
        return True
    return _not_exists

def schema_exists(schema_name: str):
    def _schema_exists(db: Database):
        return db.inspector.has_schema(schema_name)
    return _schema_exists

def view_exists(schema_name: str, *view_names: str):
    def _view_exists(db: Database):
        for view_name in view_names:
            if not view_name in db.inspector.get_view_names(schema_name):
                return False
        return True
    return _view_exists


def has_fks(*table_names: str):
    def _has_fks(db: Database):
        for table_name in table_names:
            schema, table = table_name.split('.')
            fks = db.inspector.get_foreign_keys(table, schema=schema)
            if len(fks) == 0:
                return False
        return True
    return _has_fks

class ApplicationStatus(Enum):
    CANT_APPLY = "cant_apply"
    CAN_APPLY = "can_apply"
    APPLIED = "applied"

class Migration:
    """This will eventually be merged with the migration system in macrostrat.dinosaur"""

    name: str
    description: str
    subsystem: str
    depends_on: list[str] = []
    
    # List of functions that must evaluate to true before the migration can be run
    preconditions: list[DbEvaluator] = []
    # List of functions that should evaluate to true after the migration has run successfully
    postconditions: list[DbEvaluator] = []

    def should_apply(self, database: Database) -> ApplicationStatus:
        """ Determine whether this migration can run, or has already run.  """
        # If all post-conditions are met, the migration is already applied
        if all([cond(database) for cond in self.postconditions]):
           return ApplicationStatus.APPLIED
        # Else if all pre-conditions are met, the migration can be applied
        elif all([cond(database) for cond in self.preconditions]):
           return ApplicationStatus.CAN_APPLY
        # Else, can't apply
        else:
            return ApplicationStatus.CANT_APPLY

    def apply(self, database: Database):
        """ Apply the migrations defined by this class. By default, run every sql file 
        in the same directory as the class definition. """
        child_cls_dir = Path(inspect.getfile(self.__class__)).parent
        database.run_fixtures(child_cls_dir)

    def is_satisfied(self, database: Database):
        """In some cases, we may want to note that a migration does not need to be run
        (e.g. if the database is already in the correct state) without actually running it.
        """
        return not self.should_apply(database)
