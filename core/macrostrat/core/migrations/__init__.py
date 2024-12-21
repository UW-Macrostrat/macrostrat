import inspect
from enum import Enum
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Callable

from macrostrat.database import Database
from rich import print

from ..database import get_database, refresh_database

""" Higher-order functions that return a function that evaluates whether a condition is met on the database """
DbEvaluator = Callable[[Database], bool]


def exists(schema: str, *table_names: str) -> DbEvaluator:
    """Return a function that evaluates to true when every given table in the given schema exists"""
    return lambda db: all(db.inspector.has_table(t, schema=schema) for t in table_names)


def not_exists(schema: str, *table_names: str) -> DbEvaluator:
    """Return a function that evaluates to true when every given table in the given schema doesn't exist"""
    return lambda db: all(
        not db.inspector.has_table(t, schema=schema) for t in table_names
    )


def schema_exists(schema: str) -> DbEvaluator:
    """Return a function that evaluates to true when the given schema exists"""
    return lambda db: db.inspector.has_schema(schema)


def view_exists(schema: str, *view_names: str) -> DbEvaluator:
    """Return a function that evaluates to true when every given view in the given schema exists"""
    return lambda db: all(v in db.inspector.get_view_names(schema) for v in view_names)


def has_fks(schema: str, *table_names: str) -> DbEvaluator:
    """Return a function that evaluates to true when every given table in the given schema has at least one foreign key"""
    return lambda db: all(
        db.inspector.has_table(t, schema=schema)
        and len(db.inspector.get_foreign_keys(t, schema=schema))
        for t in table_names
    )


def custom_type_exists(schema: str, *type_names: str) -> DbEvaluator:
    """Return a function that evaluates to true when every given custom type in the given schema exists"""
    return lambda db: all(db.inspector.has_type(t, schema=schema) for t in type_names)


def _not(f: DbEvaluator) -> DbEvaluator:
    """Return a function that evaluates to true when the given function evaluates to false"""
    return lambda db: not f(db)


class ApplicationStatus(Enum):
    """Enum for the possible"""

    # The preconditions for this migration aren't met, so it can't be applied
    CANT_APPLY = "cant_apply"

    # The preconditions for this migration are met but the postconditions aren't met, so it can be applied
    CAN_APPLY = "can_apply"

    # The postconditions for this migration are met, so it doesn't need to be applied
    APPLIED = "applied"


class Migration:
    """Class defining a set of SQL changes to be applied to the database, as well as checks for
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

    # Flag for whether running this migration will cause data changes in the database in addition to
    # schema changes
    destructive: bool = False

    def should_apply(self, database: Database) -> ApplicationStatus:
        """Determine whether this migration can run, or has already run."""
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
        """Apply the migrations defined by this class. By default, run every sql file
        in the same directory as the class definition."""
        child_cls_dir = Path(inspect.getfile(self.__class__)).parent
        database.run_fixtures(child_cls_dir)


def run_migrations(
    apply: bool = False,
    name: str = None,
    force: bool = False,
    data_changes: bool = False,
    subsystem: str = None,
):
    """Apply database migrations"""
    db = get_database()

    # Check if migrations need to be run and if not, run them

    if force and not name:
        raise ValueError("--force can only be applied with --name")

    # Find all subclasses of Migration among imported modules
    migrations = Migration.__subclasses__()

    # Instantiate each migration, then sort topologically according to dependency order
    instances = [cls() for cls in migrations]
    graph = {inst.name: inst.depends_on for inst in instances}
    order = list(TopologicalSorter(graph).static_order())
    instances.sort(key=lambda i: order.index(i.name))

    # While iterating over migrations, keep track of which have already applied
    completed_migrations = []

    for _migration in instances:
        _name = _migration.name
        _subsystem = getattr(_migration, "subsystem", None)

        # Check whether the migration is capable of applying, or has already applied
        apply_status = _migration.should_apply(db)
        if apply_status == ApplicationStatus.APPLIED:
            completed_migrations.append(_migration.name)

        # If --name is specified, only run the migration with the matching name
        if name is not None and name != _name:
            continue

        # If --subsystem is specified, only run migrations that match the subsystem
        if subsystem is not None and subsystem != _subsystem:
            continue

        # By default, don't run migrations that depend on other non-applied migrations
        dependencies_met = all(d in completed_migrations for d in _migration.depends_on)
        if not dependencies_met and not force:
            print(f"Dependencies not met for migration [cyan]{_name}[/cyan]")
            continue

        if force or apply_status == ApplicationStatus.CAN_APPLY:
            if not apply:
                print(f"Would apply migration [cyan]{_name}[/cyan]")
            else:
                if _migration.destructive and not data_changes and not force:
                    print(
                        f"Migration [cyan]{_name}[/cyan] would alter data in the database. Run with --force or --data-changes"
                    )
                    return

                print(f"Applying migration [cyan]{_name}[/cyan]")
                _migration.apply(db)
                # After running migration, reload the database and confirm that application was sucessful
                db = refresh_database()
                if _migration.should_apply(db) == ApplicationStatus.APPLIED:
                    completed_migrations.append(_migration.name)
        elif apply_status == ApplicationStatus.APPLIED:
            print(f"Migration [cyan]{_name}[/cyan] already applied")
        else:
            print(f"Migration [cyan]{_name}[/cyan] cannot apply")

        # Short circuit after applying the migration specified by --name
        if name is not None and name == _name:
            break

    # Notify PostgREST to reload the schema cache
    db.run_sql("NOTIFY pgrst, 'reload schema';")


def migration_has_been_run(*names: str):
    db = get_db()
    migrations = Migration.__subclasses__()

    available_migrations = {m.name for m in migrations}
    if not set(names).issubset(available_migrations):
        raise ValueError(f"Unknown migrations: {set(names) - available_migrations}")

    for _migration in migrations:
        if _migration.name in names:
            apply_status = _migration.should_apply(db)
            if apply_status != ApplicationStatus.APPLIED:
                return True
    return False
