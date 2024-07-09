from .._legacy import get_db
from rich import print
from .base import Migration
from typing import ClassVar
from .partition_maps import PartitionMapsMigration
from .partition_carto import PartitionCartoMigration

def run_migrations(apply: bool = False, name: str = None, force: bool = False):
    """Apply database migrations"""
    db = get_db()

    # Check if migrations need to be run and if not, run them

    if force and not name:
        raise ValueError("--force can only be applied with --name")

    migrations: list[ClassVar[Migration]] = [
        PartitionMapsMigration,
        PartitionCartoMigration,
    ]

    for cls in migrations:
        # Initialize migration
        _migration = cls()
        _name = _migration.name
        if name is not None and name != _name:
            continue

        if _migration.should_apply(db) or force:
            if not apply:
                print(f"Would apply migration [cyan]{_name}[/cyan]")
            else:
                _migration.apply(db)
        else:
            print(f"Migration [cyan]{_name}[/cyan] not required")
