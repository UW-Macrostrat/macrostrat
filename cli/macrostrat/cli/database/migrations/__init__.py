from macrostrat.database import Database

from .._legacy import get_db
from rich import print
from .base import Migration, ApplicationStatus
from typing import ClassVar
from pathlib import Path
from graphlib import TopologicalSorter
from . import (
    baseline, partition_carto, partition_maps, update_macrostrat, map_source_slugs, map_sources, 
    column_builder, api_v3
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
        return has_enum(db, "schemeenum", schema="macrostrat")


def has_enum(db: Database, name: str, schema: str = None):
    sql = "select 1 from pg_type where typname = :name"
    if schema is not None:
        sql += (
            " and typnamespace = (select oid from pg_namespace where nspname = :schema)"
        )

    return db.run_query(
        f"select exists ({sql})", dict(name=name, schema=schema)
    ).scalar()


def run_migrations(apply: bool = False, name: str = None, force: bool = False):
    """Apply database migrations"""
    db = get_db()

    # Check if migrations need to be run and if not, run them

    if force and not name:
        raise ValueError("--force can only be applied with --name")

    # Find all subclasses of Migration among imported modules
    migrations = Migration.__subclasses__() 

    # Instantiate each migration, then sort alphabetically by migration name
    instances = [cls() for cls in migrations]
    graph = {inst.name: inst.depends_on for inst in instances}
    order = list(TopologicalSorter(graph).static_order())
    instances.sort(key=lambda i: order.index(i.name))

    for _migration in instances:
        # Initialize migration
        _name = _migration.name
        if name is not None and name != _name:
            continue
            
        apply_status = _migration.should_apply(db)

        if force or apply_status == ApplicationStatus.CAN_APPLY:
            if not apply:
                print(f"Would apply migration [cyan]{_name}[/cyan]")
            else:
                _migration.apply(db)
        elif apply_status == ApplicationStatus.APPLIED:
            print(f"Migration [cyan]{_name}[/cyan] already applied")
        else:
            print(f"Migration [cyan]{_name}[/cyan] cannot apply yet")
