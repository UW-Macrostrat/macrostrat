from macrostrat.database import Database

from .._legacy import get_db, refresh_db
from rich import print
from .base import Migration, ApplicationStatus
from typing import ClassVar
from pathlib import Path
from graphlib import TopologicalSorter
from . import (
    baseline, macrostrat_mariadb, partition_carto, partition_maps, update_macrostrat, map_source_slugs, map_sources, 
    column_builder, api_v3, points, maps_source_operations
)
__dir__ = Path(__file__).parent


class StorageSchemeMigration(Migration):
    name = "storage-scheme"

    depends_on = ['api-v3']

    def apply(self, db: Database):
        db.run_sql(
            """
        CREATE TYPE storage.scheme AS ENUM ('s3', 'https', 'http');
        ALTER TYPE storage.scheme ADD VALUE 'https' AFTER 's3';
        ALTER TYPE storage.scheme ADD VALUE 'http' AFTER 'https';

        -- Lock the table to prevent concurrent updates
        LOCK TABLE storage.object IN ACCESS EXCLUSIVE MODE;

        ALTER TABLE storage.object
        ALTER COLUMN scheme
              TYPE storage.scheme USING scheme::text::storage.scheme;

        -- Unlock the table
        COMMIT;

        DROP TYPE IF EXISTS macrostrat.schemeenum;
        """
        )

    def should_apply(self, db: Database):
        if has_enum(db, "schemeenum", schema="macrostrat"):
            return ApplicationStatus.CAN_APPLY
        else:
            return ApplicationStatus.APPLIED


def has_enum(db: Database, name: str, schema: str = None):
    sql = "select 1 from pg_type where typname = :name"
    if schema is not None:
        sql += (
            " and typnamespace = (select oid from pg_namespace where nspname = :schema)"
        )

    return db.run_query(
        f"select exists ({sql})", dict(name=name, schema=schema)
    ).scalar()


def run_migrations(apply: bool = False, name: str = None, force: bool = False, data_changes: bool = False):
    """Apply database migrations"""
    db = get_db()

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

        # Check whether the migration is capable of applying, or has already applied
        apply_status = _migration.should_apply(db)
        if apply_status == ApplicationStatus.APPLIED:
            completed_migrations.append(_migration.name)

        # If --name is specified, only run the migration with the matching name
        if name is not None and name != _name:
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
                    print(f"Migration [cyan]{_name}[/cyan] would alter data in the database. Run with --force or --data-changes")
                    return
                    
                print(f"Applying migration [cyan]{_name}[/cyan]")
                _migration.apply(db)
                # After running migration, reload the database and confirm that application was sucessful
                db = refresh_db()
                if _migration.should_apply(db) == ApplicationStatus.APPLIED:
                    completed_migrations.append(_migration.name)
        elif apply_status == ApplicationStatus.APPLIED:
            print(f"Migration [cyan]{_name}[/cyan] already applied")
        else:
            print(f"Migration [cyan]{_name}[/cyan] cannot apply")

        # Short circuit after applying the migration specified by --name
        if name is not None and name == _name:
            break
