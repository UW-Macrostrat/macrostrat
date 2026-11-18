"""Macrostrat's migrations, run with `macrostrat.schema_management`.

Migrations are defined in `schema/_migrations` and beside the modules that own
them (`map_topology`, `usage_stats`, `integrations`), which register theirs by
being imported.
"""

from pathlib import Path
from typing import Optional

from rich import print

from macrostrat.core.config import settings
from macrostrat.database import Database
from macrostrat.schema_management import (
    Migration,
    MigrationResult,
    MigrationRunner,
    concrete_migrations,
)
from macrostrat.schema_management import load_migrations as _load_migrations

root_migrations_dir = settings.srcroot / "schema" / "_migrations"

_loaded: set[Path] = set()


def load_migrations(migrations_dir: Path = root_migrations_dir):
    # Once: a second import would define every migration again.
    if migrations_dir not in _loaded:
        _load_migrations(migrations_dir)
        _loaded.add(migrations_dir)


def migration_classes() -> list[type[Migration]]:
    """Every migration registered in this process, bar other databases'."""
    load_migrations()
    return [
        cls
        for cls in concrete_migrations()
        if getattr(cls, "database", "macrostrat") == "macrostrat"
    ]


def migration_runner(db: Optional[Database] = None) -> MigrationRunner:
    from .app import schema_definition

    return schema_definition().runner(db)


def run_migrations(
    apply: bool = False,
    name: str = None,
    force: bool = False,
    data_changes: bool = False,
    subsystem: str = None,
    dry_run: bool = False,
    legacy: bool = False,
    reapply: bool = False,
    show_applied: bool = False,
):
    """List or apply migrations on the active environment's database."""
    if dry_run:
        print("Running migrations in dry-run mode")
        return dry_run_migrations(legacy=legacy)
    return migration_runner().run(
        apply=apply,
        name=name,
        force=force,
        data_changes=data_changes,
        subsystem=subsystem,
        legacy=legacy,
        reapply=reapply,
        show_applied=show_applied,
    )


def run_migrations_in_database(
    db: Database, *, legacy=False, raise_errors=False, readiness_level=None
) -> MigrationResult:
    """Apply migrations to `db` until none remain; for a scratch database."""
    return migration_runner(db).run_to_completion(
        legacy=legacy, raise_errors=raise_errors, readiness_level=readiness_level
    )


def dry_run_migrations(legacy=False) -> MigrationResult:
    """Apply every migration to an empty throwaway cluster."""
    from .app import temporary_database_cluster

    with temporary_database_cluster(build=True) as db:
        res = run_migrations_in_database(db, legacy=legacy)
    print(f"Applied {res.n_migrations} migrations in {res.duration:.1f} seconds")
    if res.n_remaining == 0:
        print("[bold green]No more migrations to apply!")
    else:
        print(f"{res.n_remaining} migrations remaining")
    return res


def migration_has_been_run(*names: str) -> bool:
    return migration_runner().has_been_run(*names)
