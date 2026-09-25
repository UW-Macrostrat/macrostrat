import inspect
import warnings
from enum import Enum
from functools import lru_cache, total_ordering
from graphlib import TopologicalSorter
from os import environ
from time import time
from typing import Optional, Union

import docker
from pydantic import BaseModel
from rich import print

from macrostrat.core.config import settings
from macrostrat.core.database import get_database
from macrostrat.database.query import OutputMode
from macrostrat.dinosaur.cluster import database_cluster

from .inspect_utils import *

try:
    from macrostrat.core import app as _app
except Exception:
    _app = None

# canonicalize env and readiness states
_ENV_ALIASES = {
    "dev": "dev",
    "development": "dev",
    "local": "dev",
    "stage": "staging",
    "staging": "staging",
    "preprod": "staging",
    "prod": "prod",
    "production": "prod",
}
_MIN_READINESS_BY_ENV = {"dev": "alpha", "staging": "beta", "prod": "ga"}
_READINESS_ORDER = {"alpha": 0, "beta": 1, "ga": 2}


@total_ordering
class ReadinessState(Enum):
    ALPHA = "alpha"
    BETA = "beta"
    GA = "ga"

    def __gt__(self, other):
        if not isinstance(other, ReadinessState):
            return NotImplemented
        return _READINESS_ORDER[self.value] > _READINESS_ORDER[other.value]

    def __eq__(self, other):
        if not isinstance(other, ReadinessState):
            return NotImplemented
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)


# based on set_env in macrostrat/cli/macrostrat/cli/entrypoint.py
def _get_active_env() -> str:
    env = getattr(settings, "env", None)
    state = None
    if not env and _app is not None:
        state_mgr = getattr(_app, "state", None)
        if state_mgr is not None:
            state = state_mgr.get()
        if state is not None:
            env = getattr(state, "active_env", None)
    if not env:
        env = environ.get("MACROSTRAT_ENV")
    env = (env or "dev").lower()
    return _ENV_ALIASES.get(env, "development")


def _env_allows_migration(
    migration_readiness: Union[str, ReadinessState], env: str
) -> bool:
    # We prefer to use the ReadinessState enum if provided
    if isinstance(migration_readiness, ReadinessState):
        migration_readiness = migration_readiness.value
    migr_ready = (migration_readiness or "alpha").lower()
    min_ready = _MIN_READINESS_BY_ENV[_get_active_env() if env is None else env].lower()
    return _READINESS_ORDER[migr_ready] >= _READINESS_ORDER[min_ready]


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

    # Short description for the migration, printed beneath it when listed
    description: Optional[str] = None

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

    # Schema chunks to re-sync once this migration has applied: their views,
    # functions, seed data and grants are re-applied, as `macrostrat schema sync
    # --target <chunk> --no-dependents` would. For a migration that changes the
    # structure a chunk's code objects are defined against, so it need not
    # re-run the chunk's files itself. Runs before the postconditions are checked.
    sync_chunks: list[str] = []

    # Flag for whether running this migration will cause data changes in the database in addition to
    # schema changes
    destructive: bool = False

    # Flag for whether this migration only contains views/functions that don't modify the broader schema
    always_apply: bool = False

    # Flags for whether the migration can be applied in the given environment
    readiness_state: str = "alpha"

    output_mode: OutputMode = OutputMode.SUMMARY

    def __init__(self):
        pass

    def should_apply(self, database: Database) -> ApplicationStatus:
        """Determine whether this migration can run, or has already run.

        Only called once every dependency has applied, so a condition may read
        what a dependency creates."""
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
        if len(self.fixtures) == 0 and self.load_sql_files:
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
    NOT_ENV_READY = "not_env_ready"


def run_migrations(
    apply: bool = False,
    name: str = None,
    force: bool = False,
    data_changes: bool = False,
    subsystem: str = None,
    dry_run: bool = False,
    wait: bool = False,
    legacy: bool = False,
    reapply: bool = False,
    show_applied: bool = False,
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
        reapply=reapply,
        show_applied=show_applied,
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
    img_root = settings.srcroot / "base-images" / "database"

    # Build postgres pgaudit image
    img_tag = "macrostrat.local/database:latest"

    # Spin up an image with this container
    with database_cluster(img_tag, context=img_root, build=True) as db:
        return _run_migrations_in_database(db, legacy=legacy)


def _run_migrations_in_database(
    db, *, legacy=False, raise_errors=False, readiness_level=None
):
    t_start = time()

    _migrations = applyable_migrations(
        db, allow_destructive=True, legacy=legacy, readiness_level=ReadinessState.GA
    )
    _next_migrations = None
    n_total = 0
    n_migrations = len(_migrations)
    while n_migrations > 0:
        if _migrations == _next_migrations:
            print("No changes in applyable migrations, exiting")
            if raise_errors:
                raise ValueError("No migrations to apply")
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
def _get_all_migrations(
    *, legacy: bool = False, readiness_level: ReadinessState = None
):
    """
    Get all migrations in the system
    :param legacy: Include legacy migrations
    :param readiness_level: Include migrations with readiness level greater than or equal to this value
    :return: List of migration instances
    """

    migrations = _migration_classes()

    # Instantiate each migration, then sort topologically according to dependency order
    instances = [
        cls()
        for cls in migrations
        if (legacy or not getattr(cls, "legacy", False)) and hasattr(cls, "name")
    ]

    _state = lambda s: ReadinessState(s) if not isinstance(s, ReadinessState) else s

    if readiness_level is not None:
        expected_level = _state(readiness_level)
        instances = [
            inst
            for inst in instances
            if _state(getattr(inst, "readiness_state", "alpha")) >= expected_level
        ]

    graph = {inst.name: inst.depends_on for inst in instances}
    order = list(TopologicalSorter(graph).static_order())
    instances.sort(key=lambda i: order.index(i.name))
    return instances


def _migration_classes() -> list[type[Migration]]:
    """Every concrete migration class among imported modules."""
    migrations = Migration.__subclasses__()

    for cls in migrations:
        if hasattr(cls, "name"):
            # This is a concrete migration class
            continue
        # Recursively include subclasses if not concrete
        subclasses = cls.__subclasses__()
        if len(subclasses) == 0:
            warnings.warn(
                f"No subclasses or concrete implementation found for migration class {cls}"
            )
        migrations.extend(subclasses)
    return [cls for cls in migrations if hasattr(cls, "name")]


def _sync_after(db: Database, migration: Migration):
    """Re-sync the chunks a migration names, once it has applied."""
    if not migration.sync_chunks:
        return
    from .composer import selected_chunks
    from .sync import sync_schema_chunks

    chunks = [
        c for c in selected_chunks(settings.env) if c.name in migration.sync_chunks
    ]
    unknown = set(migration.sync_chunks) - {c.name for c in chunks}
    if unknown:
        print(
            f"[yellow]{migration.name} syncs {', '.join(sorted(unknown))}, which is not"
            f" a schema chunk in {settings.env}[/]"
        )
    if not chunks:
        return
    print(f"[dim]Syncing {', '.join(c.name for c in chunks)}[/]")
    report = sync_schema_chunks(db, chunks)
    for failure in report.failures:
        print(f"[red]  - {failure}")


def _undefined_dependencies(migration: Migration, defined: set[str]) -> list[str]:
    """Dependencies that name no migration at all, legacy ones included."""
    return [d for d in migration.depends_on if d not in defined]


def _dependencies_met(
    migration: Migration, completed: set[str] | list[str], present: set[str]
) -> bool:
    """Whether every dependency in this run has applied.

    A dependency that is not in the run counts as met. Migrations are removed
    once they hold in every environment, and what depended on one still stands;
    the listing names any that no longer exist, so a typo does not pass silently.
    """
    return all(d in completed for d in migration.depends_on if d in present)


def _evaluate(db: Database, instances: list[Migration]):
    """Yield each migration with its `ApplicationStatus`, in dependency order.

    A migration whose dependencies have not applied is not evaluated, and yields
    None: its conditions may read what a dependency creates.
    """
    present = {m.name for m in instances}
    completed = set()
    for migration in instances:
        status = None
        if _dependencies_met(migration, completed, present):
            status = migration.should_apply(db)
            if status == ApplicationStatus.APPLIED:
                completed.add(migration.name)
        yield migration, status


def _run_migrations(
    db: Database,
    apply: bool = False,
    name: str = None,
    force: bool = False,
    data_changes: bool = False,
    subsystem: str = None,
    verbose: bool = True,
    legacy: bool = False,
    reapply: bool = False,
    show_applied: bool = False,
) -> [Optional[int], set[str]]:
    """Apply database migrations"""
    # Start time
    t_start = time()
    cur_env = _get_active_env()

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
    listed = []
    present = {m.name for m in instances}
    defined = present | {cls.name for cls in _migration_classes()}

    # Every migration is evaluated, filtered or not, so that one named with
    # --name sees whether its dependencies have applied.
    for _migration, apply_status in _evaluate(db, instances):
        _name = _migration.name
        _subsystem = getattr(_migration, "subsystem", None)

        if apply_status == ApplicationStatus.APPLIED:
            completed_migrations.append(_name)

        # If --name is specified, only run the migration with the matching name
        if name is not None and name != _name:
            continue

        # If --subsystem is specified, only run migrations that match the subsystem
        if subsystem is not None and subsystem != _subsystem:
            continue

        _status = _get_status(
            _migration,
            completed_migrations,
            apply_status,
            data_changes=data_changes,
            env=_get_active_env(),
        )

        listed.append((_migration, _status))
        migrations_to_run.append(_migration)

    # Applied migrations last, so what needs attention is at the top, and only on
    # request (or when named). Printing only: `migrations_to_run` keeps
    # dependency order for application.
    listed.sort(key=lambda row: row[1] == MigrationState.COMPLETE)
    n_hidden = 0
    for _migration, _status in listed:
        if _status == MigrationState.COMPLETE and not (show_applied or name):
            n_hidden += 1
            continue
        _print_status(_migration.name, _status, name_max_width=name_max_width)
        undefined = _undefined_dependencies(_migration, defined)
        if undefined:
            print(
                f"    [yellow]depends on {', '.join(undefined)}, which no longer"
                " exist -- assumed met[/]"
            )
        if _migration.description:
            print(f"    [dim]{_migration.description}[/]")
        if _migration.sync_chunks:
            print(f"    [dim]then syncs {', '.join(_migration.sync_chunks)}[/]")
    if n_hidden:
        print(f"[dim]{n_hidden} already applied (--show-applied to list them)[/]")

    if not apply:
        print("\n[dim]To apply the migrations, run with --apply")
        return (None, set())

    run_counter = 0

    for _migration in migrations_to_run:
        _name = _migration.name
        _subsystem = getattr(_migration, "subsystem", None)
        if not _env_allows_migration(
            getattr(_migration, "readiness_state", "alpha"), cur_env
        ):
            continue
        # By default, don't run migrations that depend on other non-applied migrations
        dependencies_met = _dependencies_met(_migration, completed_migrations, present)

        if not force:
            if not dependencies_met:
                continue

            if (
                _name in completed_migrations
                and not reapply
                and not _migration.always_apply
            ):
                continue

            if _migration.destructive and not data_changes:
                continue

            # Evaluated here rather than trusted from the listing: a dependency
            # applied earlier in this run can be what makes the conditions hold,
            # or evaluable at all.
            apply_status = _migration.should_apply(db)
            if apply_status == ApplicationStatus.CANT_APPLY:
                print(f"\n[dim]Skipping [cyan]{_name}[/]: preconditions not met[/]")
                continue
            if apply_status == ApplicationStatus.APPLIED and not reapply:
                completed_migrations.append(_name)
                continue

        # Hack to allow migrations to follow output mode
        _migration.output_mode = output_mode

        print(f"\nApplying migration [bold cyan]{_name}[/]...")
        _migration.apply(db)
        _sync_after(db, _migration)
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


def applyable_migrations(
    db, *, allow_destructive=False, legacy=False, readiness_level=None
) -> set[str]:
    """Check if there are any migrations that can be applied"""
    _res = set()
    migrations = _get_all_migrations(legacy=legacy, readiness_level=readiness_level)
    for _migration, apply_status in _evaluate(db, migrations):
        if _migration.destructive and not allow_destructive:
            continue
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
    _migration: Migration,
    completed_migrations: set[str],
    apply_status: Optional[ApplicationStatus],
    data_changes: bool = False,
    env: Optional[str] = None,
) -> MigrationState:
    """Get the status of a migration. `apply_status` is None for one that was not
    evaluated because a dependency has not applied."""
    name = _migration.name
    env = env or _get_active_env()

    if name in completed_migrations:
        return MigrationState.COMPLETE

    if not _env_allows_migration(getattr(_migration, "readiness_state", "alpha"), env):
        return MigrationState.NOT_ENV_READY

    # By default, don't run migrations that depend on other non-applied migrations
    if apply_status is None:
        return MigrationState.UNMET_DEPENDENCIES

    if _migration.always_apply:
        return MigrationState.ALWAYS_APPLY

    if apply_status == ApplicationStatus.CANT_APPLY:
        return MigrationState.CANNOT_APPLY

    if _migration.destructive and not data_changes:
        return MigrationState.DISALLOWED
    return MigrationState.SHOULD_APPLY


def _print_status(name, status: MigrationState, *, name_max_width=40):
    padding = " " * (name_max_width - len(name))
    print(f"- [bold cyan]{name}[/]: " + padding, end="")
    if status == MigrationState.COMPLETE:
        print("[green]already applied[/green]")
    elif status == MigrationState.UNMET_DEPENDENCIES:
        print("[orange]has unmet dependencies[/orange]")
    elif status == MigrationState.CANNOT_APPLY:
        print("[red]cannot be applied[/red]")
    elif status == MigrationState.SHOULD_APPLY:
        print("[orange]should be applied[/orange]")
    elif status == MigrationState.ALWAYS_APPLY:
        print("[yellow] always applied[/yellow]")
    elif status == MigrationState.DISALLOWED:
        print("[red]cannot be applied without --force or --data-changes[/red]")
    elif status == MigrationState.NOT_ENV_READY:
        cur_env = _get_active_env()
        print(f"[red]not {cur_env} ready[/red]")
    else:
        raise ValueError(f"Unknown migration status: {status}")
