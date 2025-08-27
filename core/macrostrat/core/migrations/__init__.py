import inspect
from enum import Enum
from functools import lru_cache
from graphlib import TopologicalSorter
from pathlib import Path
from time import time
from typing import Callable, Iterable, Optional

import docker
from pydantic import BaseModel
from rich import print

from macrostrat.database import Database
from macrostrat.database.utils import OutputMode
from macrostrat.dinosaur.upgrade_cluster.utils import database_cluster

from ..config import settings
from ..database import get_database

""" Higher-order functions that return a function that evaluates whether a condition is met on the database """
DbEvaluator = Callable[[Database], bool]

PathDependency = Callable[["Migration"], Path] | Path
DBCallable = Callable[[Database], None]


def exists(schema: str, *table_names: str) -> DbEvaluator:
    """Return a function that evaluates to true when every given table in the given schema exists"""
    return lambda db: all(db.inspector.has_table(t, schema=schema) for t in table_names)


def not_exists(schema: str, *table_names: str) -> DbEvaluator:
    """Return a function that evaluates to true when every given table in the given schema doesn't exist"""
    return _not(exists(schema, *table_names))


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


def has_columns(schema: str, table: str, *fields: str, allow_view=False) -> DbEvaluator:
    """Return a function that evaluates to true when every given field in the given table exists"""

    def _has_fields(db: Database) -> bool:
        _has_table = db.inspector.has_table(table, schema=schema)
        if not _has_table and not allow_view:
            return False
        _has_view = table in db.inspector.get_view_names(schema)
        if not _has_table and not _has_view:
            return False
        columns = db.inspector.get_columns(table, schema=schema)
        col_names = [c["name"] for c in columns]
        return all(f in col_names for f in fields)

    return _has_fields


def _not(f: DbEvaluator) -> DbEvaluator:
    """Return a function that evaluates to true when the given function evaluates to false"""
    return lambda db: not f(db)


def _any(f: Iterable[DbEvaluator]) -> DbEvaluator:
    """Return a function that evaluates to true when any of the given functions evaluate to true"""

    def _any_f(db: Database) -> bool:
        return any(cond(db) for cond in f)

    return _any_f


class ApplicationStatus(Enum):
    """Enum for the possible"""

    # The preconditions for this migration aren't met, so it can't be applied
    CANT_APPLY = "cant_apply"

    # The preconditions for this migration are met but the postconditions aren't met, so it can be applied
    CAN_APPLY = "can_apply"

    # The postconditions for this migration are met, so it doesn't need to be applied
    APPLIED = "applied"


class Migration:
    """Class defining a set of sql changes to be applied to the database, as well as checks for
    whether the migration can be applied to the current state of the database
    """

    # Unique name for the migration
    name: str

    # Short description for the migration
    description: str

    # Portion of the database to which this migration applies
    subsystem: str

    # List of migration names that must be run before this migration
    depends_on: list[str] = []

    # List of checks on the database that must all evaluate to true before the migration can be run
    preconditions: list[DbEvaluator] = []

    # List of checks on the database that should all evaluate to true after the migration has run successfully
    postconditions: list[DbEvaluator] = []

    # Should sql be loaded from the directory of the migration class
    load_sql_files: bool | Path = True

    # Fixtures to run after loaded sql
    fixtures: list[Path | DBCallable] = []

    # Flag for whether running this migration will cause data changes in the database in addition to
    # schema changes
    destructive: bool = False

    # Flag for whether this migration only contains views/functions that don't modify the broader schema
    always_apply: bool = False

    output_mode: OutputMode = OutputMode.SUMMARY

    def should_apply(self, database: Database) -> ApplicationStatus:
        """Determine whether this migration can run, or has already run."""
        if self.always_apply:
            return ApplicationStatus.CAN_APPLY
        # If all post-conditions are met, the migration is already applied
        if all([cond(database) for cond in self.postconditions]):
            return ApplicationStatus.APPLIED
        # Else if all pre-conditions are met, the migration can be applied
        elif all([cond(database) for cond in self.preconditions]):
            return ApplicationStatus.CAN_APPLY
        # Else, can't apply
        else:
            return ApplicationStatus.CANT_APPLY

    def apply(self, database: Database) -> ApplicationStatus:
        """Apply the migrations defined by this class. By default, run every sql file
        in the same directory as the class definition."""
        if len(self.fixtures) == 0:
            # Automatically load fixtures from the same directory as the migration
            sql_dir = Path(inspect.getfile(self.__class__)).parent
            database.run_fixtures(sql_dir, output_mode=self.output_mode)
            return

        for fixture in self.fixtures:
            if callable(fixture):
                fixture(database)
            elif isinstance(fixture, Path):
                database.run_fixtures(fixture, output_mode=self.output_mode)
            else:
                raise ValueError(f"Fixture {fixture} should be a callable or a Path")


class MigrationState(Enum):
    """Enum for the possible states of a migration before application"""

    COMPLETE = "complete"
    UNMET_DEPENDENCIES = "unmet_dependencies"
    CANNOT_APPLY = "cannot_apply"
    SHOULD_APPLY = "should_apply"
    DISALLOWED = "disallowed"
    # The migration always applies, regardless of the state of the database
    ALWAYS_APPLY = "always_apply"


def run_migrations(
    apply: bool = False,
    name: str = None,
    force: bool = False,
    data_changes: bool = False,
    subsystem: str = None,
    dry_run: bool = False,
    wait: bool = False,
    legacy: bool = False,
):

    if dry_run:
        print("Running migrations in dry-run mode")
        dry_run_migrations(wait=True, legacy=legacy)
        return

    db = get_database()
    _run_migrations(
        db,
        apply=apply,
        name=name,
        force=force,
        data_changes=data_changes,
        subsystem=subsystem,
        legacy=legacy,
    )


class MigrationResult(BaseModel):
    n_migrations: int
    n_remaining: int
    duration: float


def dry_run_migrations(wait=False, legacy=False):
    res = _dry_run_migrations(legacy=legacy)

    print(f"Applied {res.n_migrations} migrations in {res.duration:.1f} seconds")
    if res.n_remaining == 0:
        print("[bold green]No more migrations to apply!")
    else:
        print(f"{res.n_remaining} migrations remaining")

    if wait:
        print(res)
        input("Press Enter to continue...")

    return res


def _dry_run_migrations(legacy=False):
    # Spin up a docker container with a temporary database
    image = settings.get("pg_database_container", "postgres:15")

    client = docker.from_env()

    img_root = settings.srcroot / "base-images" / "database"

    # Build postgres pgaudit image
    img_tag = "macrostrat-local-database:latest"

    client.images.build(path=str(img_root), tag=img_tag)

    # Spin up an image with this container
    port = 54884
    with database_cluster(client, img_tag, port=port) as container:
        url = f"postgresql://postgres@localhost:{port}/postgres"
        db = Database(url)
        return _run_migrations_in_database(db, legacy=legacy)


def _run_migrations_in_database(db, legacy=False):
    t_start = time()

    _migrations = applyable_migrations(db, allow_destructive=True, legacy=legacy)
    _next_migrations = None
    n_total = 0
    n_migrations = len(_migrations)
    while n_migrations > 0:

        if _migrations == _next_migrations:
            print("No changes in applyable migrations, exiting")
            break

        _migrations = _next_migrations
        n_applied, completed_migrations = _run_migrations(
            db, apply=True, data_changes=True, legacy=legacy
        )
        n_total += n_applied

        _next_migrations = applyable_migrations(
            db, allow_destructive=True, legacy=legacy
        )
        # Make sure that we don't have completed migrations in the applyable set
        _next_migrations = _next_migrations - completed_migrations
        print("Remaining migrations:", _next_migrations)

        n_migrations = len(_next_migrations)

    t_end = time()

    return MigrationResult(
        n_migrations=n_total, n_remaining=n_migrations, duration=t_end - t_start
    )


@lru_cache(10)
def _get_all_migrations(legacy: bool = False):
    """
    Get all migrations in the system
    :param legacy: Include legacy migrations
    :return: List of migration instances
    """

    # Find all subclasses of Migration among imported modules
    migrations = Migration.__subclasses__()

    # Instantiate each migration, then sort topologically according to dependency order
    instances = [
        cls() for cls in migrations if legacy or not getattr(cls, "legacy", False)
    ]
    graph = {inst.name: inst.depends_on for inst in instances}
    order = list(TopologicalSorter(graph).static_order())
    instances.sort(key=lambda i: order.index(i.name))
    return instances


def _run_migrations(
    db: Database,
    apply: bool = False,
    name: str = None,
    force: bool = False,
    data_changes: bool = False,
    subsystem: str = None,
    verbose: bool = True,
    legacy: bool = False,
) -> [Optional[int], set[str]]:
    """Apply database migrations"""
    # Start time
    t_start = time()

    # Check if migrations need to be run and if not, run them

    if force and not name:
        raise ValueError("--force can only be applied with --name")

    instances = _get_all_migrations(legacy=legacy)

    output_mode = OutputMode.SUMMARY if verbose else OutputMode.NONE

    # While iterating over migrations, keep track of which have already applied
    completed_migrations = []
    failed_migrations = []

    # Get max width of migration names for formatting
    name_max_width = max(len(m.name) for m in instances)

    print("Migrations:")

    migrations_to_run = []

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

        _status = _get_status(_migration, completed_migrations)

        _print_status(_name, _status, name_max_width=name_max_width)

        migrations_to_run.append(_migration)

    if not apply:
        print("\n[dim]To apply the migrations, run with --apply")
        return (None, set())

    run_counter = 0

    for _migration in migrations_to_run:
        _name = _migration.name
        _subsystem = getattr(_migration, "subsystem", None)

        # By default, don't run migrations that depend on other non-applied migrations
        dependencies_met = all(d in completed_migrations for d in _migration.depends_on)

        if not force:
            if not dependencies_met:
                continue

            if _name in completed_migrations:
                continue

            if _migration.destructive and not data_changes:
                continue

        # Hack to allow migrations to follow output mode
        _migration.output_mode = output_mode
        _migration.apply(db)
        run_counter += 1
        # After running migration, reload the database and confirm that application was sucessful
        db.refresh_schema()

        if (
            _migration.should_apply(db) != ApplicationStatus.APPLIED
            and not _migration.always_apply
        ):
            failed_migrations.append(_migration.name)
            continue

        completed_migrations.append(_migration.name)

    # Notify PostgREST to reload the schema cache
    db.run_sql("NOTIFY pgrst, 'reload schema';")

    t_delta = time() - t_start

    print(f"\nApplied {run_counter} migrations in {t_delta:.2f} seconds")
    print(f"Completed: {completed_migrations}")
    if failed_migrations:
        print(f"Failed: {failed_migrations}")

    return run_counter, set(completed_migrations)


def applyable_migrations(db, *, allow_destructive=False, legacy=False) -> set[str]:
    """Check if there are any migrations that can be applied"""
    _res = set()
    migrations = _get_all_migrations(legacy=legacy)
    for _migration in migrations:
        if _migration.destructive and not allow_destructive:
            continue
        apply_status = _migration.should_apply(db)
        if apply_status == ApplicationStatus.CAN_APPLY:
            _res.add(_migration.name)
    return _res


def migration_has_been_run(*names: str):
    from macrostrat.cli.database._legacy import get_db

    db = get_db()
    print(db)
    instances = [cls() for cls in Migration.__subclasses__()]
    available = {m.name for m in instances}
    missing = set(names) - available
    if missing:
        raise ValueError(f"Unknown migrations: {missing}")

    # return True only if all requested migrations are already APPLIED
    for m in instances:
        if m.name in names:
            if m.should_apply(db) is not ApplicationStatus.APPLIED:
                return False
    return True


def _get_status(
    _migration: Migration, completed_migrations: set[str], data_changes: bool = False
) -> MigrationState:
    """Get the status of a migration"""
    name = _migration.name

    # By default, don't run migrations that depend on other non-applied migrations
    dependencies_met = all(d in completed_migrations for d in _migration.depends_on)
    if not dependencies_met:
        return MigrationState.UNMET_DEPENDENCIES

    if _migration.always_apply:
        return MigrationState.ALWAYS_APPLY

    if name in completed_migrations:
        return MigrationState.COMPLETE

    if _migration.destructive and not data_changes:
        return MigrationState.DISALLOWED
    return MigrationState.SHOULD_APPLY


def _print_status(name, status: MigrationState, *, name_max_width=40):
    padding = " " * (name_max_width - len(name))
    print(f"- [bold cyan]{name}[/]: " + padding, end="")
    if status == MigrationState.COMPLETE:
        print("[green]already applied[/green]")
    elif status == MigrationState.UNMET_DEPENDENCIES:
        print("[yellow]has unmet dependencies[/yellow]")
    elif status == MigrationState.CANNOT_APPLY:
        print("[red]cannot be applied[/red]")
    elif status == MigrationState.SHOULD_APPLY:
        print("[yellow]should be applied[/yellow]")
    elif status == MigrationState.ALWAYS_APPLY:
        print("[yellow] always applied[/yellow]")
    elif status == MigrationState.DISALLOWED:
        print("[red]cannot be applied without --force or --data-changes[/red]")
    else:
        raise ValueError(f"Unknown migration status: {status}")
