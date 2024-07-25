from macrostrat.database import Database
from pathlib import Path
import inspect
from typing import Callable
from enum import Enum

""" Higher-order functions that return a function that evaluates whether a condition is met on the database """
DbEvaluator = Callable[[Database], bool]

def exists(schema: str, *table_names: str) -> DbEvaluator:
    return lambda db: all(db.inspector.has_table(t, schema=schema) for t in table_names)

def not_exists(schema: str, *table_names: str) -> DbEvaluator:
    return lambda db: all(not db.inspector.has_table(t, schema=schema) for t in table_names)

def schema_exists(schema: str) -> DbEvaluator:
    return lambda db: db.inspector.has_schema(schema)

def view_exists(schema: str, *view_names: str) -> DbEvaluator:
    return lambda db: all(v in db.inspector.get_view_names(schema) for v in view_names)

def has_fks(schema: str, *table_names: str) -> DbEvaluator:
    return lambda db: all(
        db.inspector.has_table(t, schema=schema) and 
        len(db.inspector.get_foreign_keys(t, schema=schema)) for t in table_names)

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
