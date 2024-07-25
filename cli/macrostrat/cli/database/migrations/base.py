from macrostrat.database import Database
from pathlib import Path
import inspect
from typing import Callable
from enum import Enum

""" Higher-order functions that return a function that evaluates whether a condition is met on the database """
DbEvaluator = Callable[[Database], bool]


def exists(schema: str, *table_names: str) -> DbEvaluator:
    """ Return a function that evaluates to true when every given table in the given schema exists """
    return lambda db: all(db.inspector.has_table(t, schema=schema) for t in table_names)

def not_exists(schema: str, *table_names: str) -> DbEvaluator:
    """ Return a function that evaluates to true when every given table in the given schema doesn't exist """
    return lambda db: all(not db.inspector.has_table(t, schema=schema) for t in table_names)

def schema_exists(schema: str) -> DbEvaluator:
    """ Return a function that evaluates to true when the given schema exists """
    return lambda db: db.inspector.has_schema(schema)

def view_exists(schema: str, *view_names: str) -> DbEvaluator:
    """ Return a function that evaluates to true when every given view in the given schema exists """
    return lambda db: all(v in db.inspector.get_view_names(schema) for v in view_names)

def has_fks(schema: str, *table_names: str) -> DbEvaluator:
    """ Return a function that evaluates to true when every given table in the given schema has at least one foreign key """
    return lambda db: all(
        db.inspector.has_table(t, schema=schema) and 
        len(db.inspector.get_foreign_keys(t, schema=schema)) for t in table_names)

class ApplicationStatus(Enum):
    """ Enum for the possible """

    # The preconditions for this migration aren't met, so it can't be applied
    CANT_APPLY = "cant_apply"

    # The preconditions for this migration are met but the postconditions aren't met, so it can be applied
    CAN_APPLY = "can_apply"

    # The postconditions for this migration are met, so it doesn't need to be applied
    APPLIED = "applied"

class Migration:
    """ Class defining a set of SQL changes to be applied to the database, as well as checks for 
    whether the migration can be applied to the current state of the database
    """

    # Unique name for the migration
    name: str

    # Short description for the migration
    description: str

    # Portion of the database to which this migration applies
    subsystem: str

    # List of migration names that must 
    depends_on: list[str] = []
    
    # List of checks on the database that must all evaluate to true before the migration can be run
    preconditions: list[DbEvaluator] = []

    # List of checks on the database that should all evaluate to true after the migration has run successfully
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
