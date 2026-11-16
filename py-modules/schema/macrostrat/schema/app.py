"""Macrostrat's database schema, described for `macrostrat.schema_management`."""

from contextlib import contextmanager

from macrostrat.app_frame.environments import AccessScope
from macrostrat.core import APP_OWNER
from macrostrat.core.config import settings
from macrostrat.core.database import get_database
from macrostrat.core.safety import require_write_access
from macrostrat.schema_management import SchemaApp, reload_postgrest_schema
from macrostrat.schema_management.database.cluster import database_cluster

from . import topology  # noqa: F401 -- registers the topogeometry type
from .chunks import chunks_for_class, environment_class
from .topology import filter_topology_changes

# Bulk ingested data and extension-owned tables: never part of a diff.
EXCLUDED_SCHEMAS = ["sources", "tiger", "tiger_data"]


@contextmanager
def temporary_database_cluster(**kwargs):
    """A throwaway cluster on Macrostrat's database image."""
    image_tag = kwargs.pop("image", "macrostrat.local/database:latest")
    build_context = kwargs.pop("context", settings.srcroot / "base-images" / "database")
    optimize_for_testing = kwargs.pop("optimize", True)
    config = {"shared_preload_libraries": "pgaudit,pg_stat_statements"}
    with database_cluster(
        image_tag,
        context=build_context,
        optimize_for_testing=optimize_for_testing,
        config=config,
        **kwargs,
    ) as db:
        yield db


def _authorize(action: str, assume_yes: bool):
    require_write_access(AccessScope.Schema, assume_yes=assume_yes, action=action)


def schema_definition() -> SchemaApp:
    """Built when a command runs: the environment is chosen per invocation."""
    from .migrations import migration_classes

    return SchemaApp(
        name="macrostrat",
        database=get_database,
        chunks=chunks_for_class,
        schema_dir=settings.srcroot / "schema",
        migrations=migration_classes(),
        environment=str(settings.env),
        env_class=environment_class(None),
        owner=APP_OWNER,
        planning_database=temporary_database_cluster,
        excluded_schemas=EXCLUDED_SCHEMAS,
        prepare_diff=filter_topology_changes,
        authorize=_authorize,
        after_change=reload_postgrest_schema,
        source_root=settings.srcroot,
    )
